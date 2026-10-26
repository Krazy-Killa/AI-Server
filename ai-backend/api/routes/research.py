from fastapi import APIRouter

from api import runtime

router = APIRouter()


@router.post("/api/research")
async def research_endpoint(req: runtime.ResearchRequest, request: runtime.Request):
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
            runtime.logger.exception("Could not store a dashboard research message.")
            raise runtime.HTTPException(
                status_code=500, detail="Conversation history is unavailable."
            ) from error
    try:
        session = getattr(request.state, "auth_session", None)
        system_prompt = await runtime._admin_memory_prompt(session)
        if history:
            result = await runtime.asyncio.to_thread(
                runtime.run_research,
                req.message,
                history=history,
                system_prompt=system_prompt,
            )
        else:
            result = await runtime.asyncio.to_thread(
                runtime.run_research, req.message, system_prompt=system_prompt
            )
    except runtime.MemoryStoreError as error:
        raise runtime.HTTPException(
            status_code=500, detail="Shared admin memory is unavailable."
        ) from error
    except (runtime.ResearchRuntimeError, runtime.LLMRuntimeError) as error:
        runtime.logger.warning("Web research request failed: %s", error)
        raise runtime.HTTPException(status_code=503, detail=str(error)) from error
    if conversation_id and owner_id:
        try:
            await runtime.asyncio.to_thread(
                runtime.get_conversation_store().append_assistant_message,
                owner_id,
                conversation_id,
                result["reply"],
                [
                    {
                        "title": source["title"],
                        "url": source["url"],
                        "snippet": source["snippet"],
                        "page_status": source.get("page_status", "excerpt_only"),
                    }
                    for source in result["sources"]
                ],
            )
        except runtime.ConversationNotFound as error:
            raise runtime._conversation_not_found() from error
        except runtime.MemoryStoreError as error:
            runtime.logger.exception("Could not store a dashboard research reply.")
            raise runtime.HTTPException(
                status_code=500, detail="Conversation history is unavailable."
            ) from error
    return result

@router.post("/api/research/stream")
async def research_stream_endpoint(req: runtime.ResearchRequest, request: runtime.Request):
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
            runtime.logger.exception("Could not store a dashboard research message.")
            raise runtime.HTTPException(
                status_code=500, detail="Conversation history is unavailable."
            ) from error

    try:
        session = getattr(request.state, "auth_session", None)
        system_prompt = await runtime._admin_memory_prompt(session)
        prepared = await runtime.asyncio.to_thread(
            runtime.prepare_research, req.message, system_prompt
        )
    except runtime.MemoryStoreError as error:
        raise runtime.HTTPException(
            status_code=500, detail="Shared admin memory is unavailable."
        ) from error
    except runtime.ResearchRuntimeError as error:
        runtime.logger.warning("Web research request failed: %s", error)
        raise runtime.HTTPException(status_code=503, detail=str(error)) from error

    started_at = runtime.monotonic()

    def encode_event(event: str, payload: dict[str, object]) -> str:
        data = runtime.json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        return f"event: {event}\ndata: {data}\n\n"

    def response_events():
        stream = runtime.stream_research(prepared, history=history)
        full_reply: list[str] = []
        try:
            yield encode_event(
                "sources",
                {
                    "sources": prepared["sources"],
                    "search_latency_ms": prepared["search_latency_ms"],
                },
            )
            for chunk in stream:
                full_reply.append(chunk)
                yield encode_event("token", {"content": chunk})

            if conversation_id and owner_id:
                runtime.get_conversation_store().append_assistant_message(
                    owner_id,
                    conversation_id,
                    "".join(full_reply),
                    [
                        {
                            "title": source["title"],
                            "url": source["url"],
                            "snippet": source["snippet"],
                            "page_status": source["page_status"],
                        }
                        for source in prepared["sources"]
                    ],
                )
        except runtime.LLMRuntimeError as error:
            runtime.logger.warning("Streaming web research failed: %s", error)
            yield encode_event("error", {"detail": str(error)})
            return
        except runtime.ConversationNotFound:
            yield encode_event("error", {"detail": "Conversation not found."})
            return
        except runtime.MemoryStoreError:
            runtime.logger.exception("Could not store a dashboard research reply.")
            yield encode_event(
                "error", {"detail": "Conversation history is unavailable."}
            )
            return
        finally:
            close_stream = getattr(stream, "close", None)
            if callable(close_stream):
                with runtime.suppress(ValueError):
                    close_stream()

        yield encode_event(
            "done",
            {"latency_ms": round((runtime.monotonic() - started_at) * 1000)},
        )

    return runtime.StreamingResponse(
        response_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
