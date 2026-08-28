from typing import Any

from pydantic import BaseModel

from jinrong.domain.messages import ChatHistoryMessage


class ChatObject(BaseModel):
    id:str
    title:str
    type:str
    attributes : dict[str,Any]

class ChatBotMessage(BaseModel):
    text: str
    object: ChatObject | None = None


class ChatRequest(BaseModel):
    sender_id :str
    text : str | None = None
    object : ChatObject | None = None


class ChatResponse(BaseModel):
    message_id:str
    messages: list[ChatBotMessage]

class ChatHistoryResponse(BaseModel):
    sender_id:str
    messages:list[ChatHistoryMessage]


class SessionCreateRequest(BaseModel):
    sender_id: str


class SessionResponse(BaseModel):
    sender_id: str
    session_id: str | None = None
    status: str = "ok"


class SessionStateResponse(BaseModel):
    sender_id: str
    active_task: dict[str, Any] | None = None
    active_system_task: dict[str, Any] | None = None
    paused_tasks: list[dict[str, Any]] = []
    focused_object: dict[str, Any] | None = None
    session_count: int = 0
    current_session_id: str | None = None