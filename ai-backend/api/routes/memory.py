from fastapi import APIRouter

from api import runtime

router = APIRouter()


@router.get("/api/interface/conversation")
async def admin_interface_conversation():
    try:
        conversation = await runtime.asyncio.to_thread(
            runtime.get_conversation_store().get_admin_interface_conversation
        )
    except runtime.MemoryStoreError as error:
        runtime.logger.exception("Could not load the shared AI Interface conversation.")
        raise runtime.HTTPException(
            status_code=500, detail="The shared AI Interface is unavailable."
        ) from error
    return conversation

@router.post("/api/interface/chat")
async def admin_interface_chat(req: runtime.InterfaceChatRequest, request: runtime.Request):
    session = getattr(request.state, "auth_session", None)
    if session is None or session.role != "admin":
        raise runtime.HTTPException(status_code=403, detail="Administrator access is required.")

    async with runtime.admin_interface_lock:
        store = runtime.get_conversation_store()
        author_id = f"{session.username} ({session.provider})"
        try:
            conversation = await runtime.asyncio.to_thread(
                store.get_admin_interface_conversation
            )
            history = await runtime.asyncio.to_thread(
                store.begin_user_turn,
                runtime.ADMIN_INTERFACE_OWNER,
                runtime.ADMIN_INTERFACE_CONVERSATION_ID,
                req.message,
                author_id,
            )
        except runtime.MemoryStoreError as error:
            runtime.logger.exception("Could not store a shared AI Interface message.")
            raise runtime.HTTPException(
                status_code=500, detail="The shared AI Interface is unavailable."
            ) from error

        try:
            prompts = [
                (
                    "You are the server operations interface in a single persistent "
                    "conversation shared by dashboard administrators. Identify the "
                    "current administrator using the signed-in identity and distinguish "
                    "prior administrator turns by their server-provided attribution. "
                    "Private AI Chat conversations are separate and unavailable to you; "
                    "never claim access to or disclose their contents. This console is "
                    "read-only except for an explicitly requested diagnostics observation. "
                    "Do not claim to run server commands, change configuration, repair "
                    "services, or enter maintenance. Every message and reply here is "
                    "visible to all administrators. Do not solicit or repeat passwords, "
                    "credentials, personal details, or other private information."
                ),
                await runtime._admin_memory_prompt(session),
                await runtime._diagnostics_prompt_for_request(req.message, request),
            ]
            system_prompt = "\n\n".join(prompt for prompt in prompts if prompt)
            completion = await runtime.asyncio.to_thread(
                runtime.run_llm, req.message, system_prompt, history=history
            )
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
            runtime.logger.warning("AI Interface request failed: %s", error)
            raise runtime.HTTPException(status_code=503, detail=str(error)) from error

        try:
            await runtime.asyncio.to_thread(
                store.append_assistant_message,
                runtime.ADMIN_INTERFACE_OWNER,
                str(conversation["conversation_id"]),
                completion["reply"],
            )
        except (runtime.ConversationNotFound, runtime.MemoryStoreError) as error:
            runtime.logger.exception("Could not store an AI Interface reply.")
            raise runtime.HTTPException(
                status_code=500, detail="The shared AI Interface is unavailable."
            ) from error
        return completion

@router.get("/api/memory/conversations")
async def list_conversations(
    request: runtime.Request,
    limit: int = runtime.Query(default=50, ge=1, le=runtime.MAX_CONVERSATION_LIST),
):
    try:
        conversations = await runtime.asyncio.to_thread(
            runtime.get_conversation_store().list_conversations,
            runtime._memory_owner(request),
            limit,
        )
    except runtime.MemoryStoreError as error:
        runtime.logger.exception("Could not list account conversation history.")
        raise runtime.HTTPException(
            status_code=500, detail="Conversation history is unavailable."
        ) from error
    return {"conversations": conversations, "count": len(conversations)}

@router.post("/api/memory/conversations", status_code=201)
async def create_conversation(request: runtime.Request):
    try:
        conversation = await runtime.asyncio.to_thread(
            runtime.get_conversation_store().create_conversation, runtime._memory_owner(request)
        )
    except runtime.MemoryStoreError as error:
        runtime.logger.exception("Could not create an account conversation.")
        raise runtime.HTTPException(
            status_code=500, detail="Conversation history is unavailable."
        ) from error
    return conversation

@router.get("/api/memory/conversations/{conversation_id}")
async def read_conversation(request: runtime.Request, conversation_id: runtime.uuid.UUID):
    try:
        conversation = await runtime.asyncio.to_thread(
            runtime.get_conversation_store().get_conversation,
            runtime._memory_owner(request),
            str(conversation_id),
        )
    except runtime.ConversationNotFound as error:
        raise runtime._conversation_not_found() from error
    except runtime.MemoryStoreError as error:
        runtime.logger.exception("Could not read an account conversation.")
        raise runtime.HTTPException(
            status_code=500, detail="Conversation history is unavailable."
        ) from error
    return conversation

@router.delete("/api/memory/conversations/{conversation_id}")
async def remove_conversation(request: runtime.Request, conversation_id: runtime.uuid.UUID):
    try:
        await runtime.asyncio.to_thread(
            runtime.get_conversation_store().delete_conversation,
            runtime._memory_owner(request),
            str(conversation_id),
        )
    except runtime.ConversationNotFound as error:
        raise runtime._conversation_not_found() from error
    except runtime.MemoryStoreError as error:
        runtime.logger.exception("Could not delete an account conversation.")
        raise runtime.HTTPException(
            status_code=500, detail="Conversation history is unavailable."
        ) from error
    return {"deleted": True}

@router.get("/api/memory/shared-insights")
async def list_shared_insights():
    try:
        insights = await runtime.asyncio.to_thread(
            runtime.get_conversation_store().list_shared_insights
        )
    except runtime.MemoryStoreError as error:
        runtime.logger.exception("Could not list published admin insights.")
        raise runtime.HTTPException(
            status_code=500, detail="Shared admin memory is unavailable."
        ) from error
    return {"insights": insights, "count": len(insights)}

@router.post("/api/memory/shared-insights", status_code=201)
async def publish_shared_insight(req: runtime.SharedInsightRequest, request: runtime.Request):
    session = getattr(request.state, "auth_session", None)
    if session is None:
        raise runtime.HTTPException(status_code=403, detail="An admin session is required.")
    try:
        insight = await runtime.asyncio.to_thread(
            runtime.get_conversation_store().add_shared_insight,
            req.content,
            f"{session.provider}:{session.username}",
        )
    except ValueError as error:
        raise runtime.HTTPException(status_code=422, detail=str(error)) from error
    except runtime.SharedInsightLimitReached as error:
        raise runtime.HTTPException(
            status_code=409,
            detail="Shared admin memory is full. Delete an outdated insight first.",
        ) from error
    except runtime.MemoryStoreError as error:
        runtime.logger.exception("Could not publish an admin insight.")
        raise runtime.HTTPException(
            status_code=500, detail="Shared admin memory is unavailable."
        ) from error
    return insight

@router.delete("/api/memory/shared-insights/{insight_id}")
async def remove_shared_insight(insight_id: int):
    try:
        await runtime.asyncio.to_thread(
            runtime.get_conversation_store().delete_shared_insight, insight_id
        )
    except runtime.SharedInsightNotFound as error:
        raise runtime.HTTPException(status_code=404, detail="Shared insight not found.") from error
    except runtime.MemoryStoreError as error:
        runtime.logger.exception("Could not delete a published admin insight.")
        raise runtime.HTTPException(
            status_code=500, detail="Shared admin memory is unavailable."
        ) from error
    return {"deleted": True}
