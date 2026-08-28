


from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class MessageType(Enum):
    TEXT = "text"
    OBJECT = "object"


# 业务对象类型 -> 任务流槽位名的映射（点击卡片时用于自动填槽）
OBJECT_TYPE_TO_SLOT: dict[str, str] = {
    "account": "account_no",
    "card": "card_no",
    "loan_product": "loan_product",
    "wealth_product": "wealth_product",
}


@dataclass(slots = True)
class FocusedObject:
    id: str
    title: str
    type: str
    attributes: dict[str, Any]


    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type,
            "attributes": self.attributes
        }
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FocusedObject":
        return cls(
            id=data["id"],
            title=data["title"],
            type=data["type"],
            attributes=data["attributes"]
        )

@dataclass(slots = True)
class UserMessage:
    sender_id: str
    message_id: str
    type: MessageType
    text: str | None = None
    object: FocusedObject | None = None


    def to_dict(self) -> dict[str, Any]:
        return {
            "sender_id": self.sender_id,
            "message_id": self.message_id,
            "type": self.type.value,
            "text": self.text,
            "object": self.object.to_dict() if self.object else None
        }


    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserMessage":
        return cls(
            sender_id=data["sender_id"],
            message_id=data["message_id"],
            type=MessageType(data["type"]),
            text=data.get("text"),
            object=FocusedObject.from_dict(data["object"]) if data.get("object") else None
        )

@dataclass(slots= True)
class BotMessage:
    text: str 
    object: FocusedObject | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "object": self.object.to_dict() if self.object else None
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BotMessage":
        return cls(
            text=data["text"],
            object=FocusedObject.from_dict(data["object"]) if data["object"] else None
        )


@dataclass(slots= True)
class ProcessedResult:
    message_id: str
    messages : list[BotMessage]

@dataclass(slots= True)
class ChatHistoryMessage:
    session_id: str
    role :Literal["user","bot"]
    text : str | None = None
    object: FocusedObject | None = None
