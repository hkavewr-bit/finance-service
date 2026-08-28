import asyncio
import json
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from jinrong.api.dependencies import DialogueStateServiceSep
from jinrong.api.schemas import (ChatResponse, ChatRequest, ChatBotMessage, ChatObject, ChatHistoryResponse,
                                 SessionCreateRequest, SessionResponse, SessionStateResponse)
from jinrong.domain.messages import UserMessage, MessageType, FocusedObject, ProcessedResult

router = APIRouter()


@router.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(chat_request: ChatRequest,
                        service: DialogueStateServiceSep):
    user_message = _build_user_message(chat_request)

    processed_result = await service.process_message(user_message)

    chat_response = _build_chat_response(processed_result)

    return chat_response


def _build_user_message(chat_request: ChatRequest) -> UserMessage:
    return UserMessage(
        sender_id=chat_request.sender_id,
        message_id=str(uuid.uuid4().hex),
        type=MessageType.OBJECT if chat_request.object is not None else MessageType.TEXT,
        text=chat_request.text,
        object=FocusedObject(
            id=chat_request.object.id,
            type=chat_request.object.type,
            title=chat_request.object.title,
            attributes=chat_request.object.attributes
        ) if chat_request.object is not None else None
    )


def _build_chat_response(processed_result: ProcessedResult) -> ChatResponse:
    return ChatResponse(
        message_id=processed_result.message_id,
        messages=[
            ChatBotMessage(
                text=bot_message.text,
                object=ChatObject(
                    id=bot_message.object.id,
                    type=bot_message.object.type,
                    title=bot_message.object.title,
                    attributes=bot_message.object.attributes
                ) if bot_message.object is not None else None
            )
            for bot_message in processed_result.messages
        ]
    )


@router.get("/api/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history_endpoint(sender_id: str,
                                    service: DialogueStateServiceSep
                                    ):
    chat_history_messages = await service.get_chat_history(sender_id)
    return ChatHistoryResponse(sender_id=sender_id, messages=chat_history_messages)


@router.post("/api/chat/stream")
async def chat_stream_endpoint(chat_request: ChatRequest,
                               service: DialogueStateServiceSep):
    user_message = _build_user_message(chat_request)

    processed_result = await service.process_message(user_message)

    async def event_stream():
        for bot_message in processed_result.messages:
            if bot_message.object is not None:
                yield _sse({"type": "bot_object", "object": bot_message.object.to_dict()})

            text = bot_message.text or ""

            for chunk in _chunk_text(text):
                yield _sse({"type": "bot_text", "delta": chunk})
                await asyncio.sleep(0.015)

        yield _sse({"type": "turn_end", "message_id": processed_result.message_id})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/api/session", response_model=SessionResponse)
async def create_session_endpoint(request: SessionCreateRequest,
                                  service: DialogueStateServiceSep):
    result = await service.create_session(request.sender_id)
    return SessionResponse(sender_id=result["sender_id"], session_id=result["session_id"], status="created")


@router.get("/api/session/state", response_model=SessionStateResponse)
async def get_session_state_endpoint(sender_id: str,
                                     service: DialogueStateServiceSep):
    state = await service.get_state(sender_id)
    return SessionStateResponse(**state)


@router.delete("/api/session", response_model=SessionResponse)
async def delete_session_endpoint(sender_id: str,
                                  service: DialogueStateServiceSep):
    result = await service.delete_session(sender_id)
    return SessionResponse(sender_id=result["sender_id"], status=result["status"])


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _chunk_text(text: str, size: int = 3):
    for i in range(0, len(text), size):
        yield text[i:i + size]
