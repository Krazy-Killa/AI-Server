from fastapi import APIRouter

from api import runtime

router = APIRouter()


@router.post("/api/chat")
async def chat_endpoint(req: runtime.ChatRequest, request: runtime.Request):
    history = None
    owner_id = None
    conversation_id = str(req.conversation_id) if req.conversation_id else None
    if conversation_id:
        owner_id = runtime._memory_owner(request)
        try:
            history = await runtime.asyncio.to_thread(
                runtime.get_conversation_store().begin_user_turn,
                owner_id,
                conversation_id,
                req.message,
            )
        except runtime.ConversationNotFound as error:
            raise runtime._conversation_not_found() from error
        except runtime.MemoryStoreError as error:
            runtime.logger.exception("Could not store a dashboard chat message.")
            raise runtime.HTTPException(
                status_code=500, detail="Conversation history is unavailable."
            ) from error
    try:
        session = getattr(request.state, "auth_session", None)
        diagnostics_prompt = await runtime._diagnostics_prompt_for_request(req.message, request)
        admin_prompt = await runtime._admin_memory_prompt(session)
        system_prompt = "\n\n".join(
            prompt for prompt in (admin_prompt, diagnostics_prompt) if prompt
        ) or None
        if system_prompt:
            if history:
                completion = await runtime.asyncio.to_thread(
                    runtime.run_llm, req.message, system_prompt, history=history
                )
            else:
                completion = await runtime.asyncio.to_thread(
                    runtime.run_llm, req.message, system_prompt
                )
        elif history:
            completion = await runtime.asyncio.to_thread(
                runtime.run_llm, req.message, history=history
            )
        else:
            completion = await runtime.asyncio.to_thread(runtime.run_llm, req.message)
    except runtime.DiagnosticsObservationError as error:
        raise runtime.HTTPException(
            status_code=503,
            detail="The requested diagnostics observation could not be completed.",
        ) from error
    except runtime.MemoryStoreError as error:
        raise runtime.HTTPException(
            status_code=500, detail="Shared admin memory is unavailable."
        ) from error
    except runtime.LLMRuntimeError as error:
        runtime.logger.warning("Local LLM request failed: %s", error)
        raise runtime.HTTPException(status_code=503, detail=str(error)) from error
    if conversation_id and owner_id:
        try:
            await runtime.asyncio.to_thread(
                runtime.get_conversation_store().append_assistant_message,
                owner_id,
                conversation_id,
                completion["reply"],
            )
        except runtime.ConversationNotFound as error:
            raise runtime._conversation_not_found() from error
        except runtime.MemoryStoreError as error:
            runtime.logger.exception("Could not store a dashboard assistant reply.")
            raise runtime.HTTPException(
                status_code=500, detail="Conversation history is unavailable."
            ) from error
    return completion

async def _send_error(websocket: runtime.WebSocket, detail: str) -> None:
    await websocket.send_json({"type": "error", "detail": detail})

@router.websocket("/ws/chat")
async def chat_stream_endpoint(websocket: runtime.WebSocket):
    # Browsers do not apply CORS to WebSockets, so check the origin explicitly.
    origin = websocket.headers.get("origin")
    if not runtime._origin_allowed(origin):
        runtime.logger.warning("Rejected chat WebSocket from origin %s", origin)
        await websocket.close(code=1008)
        return

    try:
        session = runtime.get_auth_store().get_session(
            websocket.cookies.get("ai_server_session")
        )
    except runtime.AuthStoreError:
        runtime.logger.exception("Could not validate chat WebSocket session.")
        await websocket.close(code=1011)
        return
    if session is None or not runtime._role_allows(session.role, "operator"):
        await websocket.close(code=1008)
        return

    cookie_response = runtime.Response()
    cookie_response.set_cookie(
        "ai_server_session",
        session.token,
        max_age=max(1, session.expires_at - int(runtime.time.time())),
        httponly=True,
        secure=runtime.settings.auth_cookie_secure,
        samesite="strict",
        path="/",
    )
    await websocket.accept(headers=cookie_response.raw_headers)
    runtime.logger.info("Chat WebSocket connected")
    try:
        while True:
            try:
                payload = await websocket.receive_json()
            except ValueError:
                await _send_error(websocket, "Messages must be valid JSON.")
                continue

            try:
                session = runtime.get_auth_store().get_session(session.token, touch=True)
            except runtime.AuthStoreError:
                runtime.logger.exception("Could not revalidate chat WebSocket session.")
                await websocket.close(code=1011)
                return
            if session is None or not runtime._role_allows(session.role, "operator"):
                await websocket.close(code=1008)
                return

            message = payload.get("message") if isinstance(payload, dict) else None
            if not isinstance(message, str) or not message.strip():
                await _send_error(websocket, "A non-empty 'message' string is required.")
                continue
            if len(message) > runtime.settings.max_chat_chars:
                await _send_error(
                    websocket,
                    f"Message exceeds {runtime.settings.max_chat_chars} characters.",
                )
                continue

            raw_conversation_id = payload.get("conversation_id")
            conversation_id = None
            owner_id = None
            history = None
            if raw_conversation_id is not None:
                if not isinstance(raw_conversation_id, str):
                    await _send_error(websocket, "Conversation ID must be a UUID string.")
                    continue
                try:
                    conversation_id = str(runtime.uuid.UUID(raw_conversation_id))
                except ValueError:
                    await _send_error(websocket, "Conversation ID must be a UUID string.")
                    continue
                owner_id = f"{session.provider}:{session.username.casefold()}"
                try:
                    history = await runtime.asyncio.to_thread(
                        runtime.get_conversation_store().begin_user_turn,
                        owner_id,
                        conversation_id,
                        message,
                    )
                except runtime.ConversationNotFound:
                    await _send_error(websocket, "Conversation not found.")
                    continue
                except runtime.MemoryStoreError:
                    runtime.logger.exception("Could not store a dashboard chat message.")
                    await websocket.close(code=1011)
                    return

            started_at = runtime.monotonic()
            try:
                system_prompt = await runtime._chat_system_prompt(message, session)
            except runtime.DiagnosticsObservationError:
                await _send_error(
                    websocket,
                    "The requested diagnostics observation could not be completed.",
                )
                continue
            except runtime.MemoryStoreError:
                await _send_error(
                    websocket, "Shared admin memory is unavailable."
                )
                continue
            if system_prompt and history:
                stream = runtime.stream_llm(
                    message, system_prompt=system_prompt, history=history
                )
            elif system_prompt:
                stream = runtime.stream_llm(message, system_prompt=system_prompt)
            elif history:
                stream = runtime.stream_llm(message, history=history)
            else:
                stream = runtime.stream_llm(message)
            full_reply = []
            sentinel = object()
            try:
                while True:
                    chunk = await runtime.asyncio.to_thread(next, stream, sentinel)
                    if chunk is sentinel:
                        break
                    full_reply.append(chunk)
                    await websocket.send_json({"type": "token", "content": chunk})
                if conversation_id and owner_id:
                    await runtime.asyncio.to_thread(
                        runtime.get_conversation_store().append_assistant_message,
                        owner_id,
                        conversation_id,
                        "".join(full_reply),
                    )
                await websocket.send_json(
                    {
                        "type": "done",
                        "latency_ms": round((runtime.monotonic() - started_at) * 1000),
                    }
                )
            except runtime.LLMRuntimeError as error:
                runtime.logger.warning("Streaming LLM request failed: %s", error)
                await _send_error(websocket, str(error))
            except runtime.ConversationNotFound:
                await _send_error(websocket, "Conversation not found.")
            except runtime.MemoryStoreError:
                runtime.logger.exception("Could not store a dashboard assistant reply.")
                await _send_error(websocket, "Conversation history is unavailable.")
            finally:
                # Closing the generator stops llama.cpp generation if the client left early.
                close_stream = getattr(stream, "close", None)
                if callable(close_stream):
                    with runtime.suppress(ValueError):
                        close_stream()
    except runtime.WebSocketDisconnect:
        runtime.logger.info("Chat WebSocket disconnected")
