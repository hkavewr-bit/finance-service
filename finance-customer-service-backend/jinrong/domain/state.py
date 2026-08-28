import time
import uuid

from dataclasses import dataclass, field
from typing import Any

from jinrong.domain.messages import BotMessage, FocusedObject, UserMessage
from jinrong.domain.contexts import SystemContext, TaskContext


@dataclass(slots=True)
class Turn:
    turn_id: str
    user_message: UserMessage
    bot_messages: list[BotMessage]

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "user_message": UserMessage.to_dict(self.user_message),
            "bot_messages": [BotMessage.to_dict(message) for message in self.bot_messages]
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Turn":
        return cls(
            turn_id=data["turn_id"],
            user_message=UserMessage.from_dict(data["user_message"]),
            bot_messages=[BotMessage.from_dict(message) for message in data["bot_messages"]]
        )


@dataclass(slots=True)
class Session:
    session_id: str
    started_at: float
    activated_at: float
    closed_at: float | None = None
    turns: list[Turn] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "activated_at": self.activated_at,
            "closed_at": self.closed_at,
            "turns": [turn.to_dict() for turn in self.turns]
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        return cls(
            session_id=data["session_id"],
            started_at=data["started_at"],
            activated_at=data["activated_at"],
            closed_at=data.get("closed_at"),
            turns=[Turn.from_dict(turn) for turn in data["turns"]]
        )


@dataclass(slots=True)
class DialogueState:
    sender_id: str
    active_task: TaskContext | None = None
    paused_tasks: list[TaskContext] = field(default_factory=list)
    active_system_task: SystemContext | None = None
    sessions: list[Session] = field(default_factory=list)
    current_session_id: str | None = None
    focused_object: FocusedObject | None = None
    pending_turn: Turn | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sender_id": self.sender_id,
            "active_task": self.active_task.to_dict() if self.active_task else None,
            "paused_tasks": [task.to_dict() for task in self.paused_tasks],
            "active_system_task": self.active_system_task.to_dict() if self.active_system_task else None,
            "sessions": [session.to_dict() for session in self.sessions],
            "current_session_id": self.current_session_id,
            "focused_object": self.focused_object.to_dict() if self.focused_object else None,
            "pending_turn": self.pending_turn.to_dict() if self.pending_turn else None
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DialogueState":
        return cls(
            sender_id=data["sender_id"],
            active_task=TaskContext.from_dict(data["active_task"]) if data["active_task"] else None,
            paused_tasks=[TaskContext.from_dict(task) for task in data["paused_tasks"]],
            active_system_task=SystemContext.from_dict(data["active_system_task"]) if data[
                "active_system_task"] else None,
            sessions=[Session.from_dict(session) for session in data["sessions"]],
            current_session_id=data["current_session_id"],
            focused_object=FocusedObject.from_dict(data["focused_object"]) if data["focused_object"] else None,
            pending_turn=Turn.from_dict(data["pending_turn"]) if data["pending_turn"] else None
        )

    def start_task(self, task_context: TaskContext):
        self.active_task = task_context

    def end_active_task(self):
        self.active_task = None

    def cancel_active_task(self):
        self.active_system_task = None
        self.active_task = None

    def remove_paused_task(self, flow_id):
        self.paused_tasks = [task for task in self.paused_tasks if task.flow_id != flow_id]

    def interrupt_active_task(self):
        self.paused_tasks.append(self.active_task)
        self.active_task = None

    def resume_task(self, flow_id: str | None = None):
        if not self.paused_tasks:
            return False
        if flow_id is None:
            self.active_task = self.paused_tasks.pop()
            return True
        for i, task in enumerate(self.paused_tasks):
            if task.flow_id == flow_id:
                self.active_task = self.paused_tasks.pop(i)
                return True

        return False

    def start_system_task(self, system_context: SystemContext):
        self.active_system_task = system_context

    def end_system_task(self):
        self.active_system_task = None

    def current_task(self):
        return self.active_system_task or self.active_task

    def set_slots(self, slots: dict[str, Any]):
        if self.active_task:
            self.active_task.slots.update(slots)

    def remove_slot(self, slot_key: str):
        if self.active_task:
            self.active_task.slots.pop(slot_key)

    def start_session(self):
        now = time.time()

        session = Session(
            session_id=str(uuid.uuid4().hex),
            started_at=now,
            activated_at=now
        )

        self.sessions.append(session)

        self.current_session_id = session.session_id

    def current_session(self):
        for session in self.sessions:
            if session.session_id == self.current_session_id:
                return session

        return None

    def close_current_session(self):
        session = self.current_session()
        if session:
            session.closed_at = time.time()
            self.current_session_id = None

    def reset_runtime_state_for_new_session(self):
        self.active_task = None
        self.paused_tasks.clear()
        self.active_system_task = None
        self.focused_object = None
        self.pending_turn = None

    def begin_turn(self, user_message: UserMessage):
        self.pending_turn = Turn(
            turn_id=str(uuid.uuid4().hex),
            user_message=user_message,
            bot_messages=[]
        )

    def commit_pending_turn(self):
        self.current_session().turns.append(self.pending_turn)

        self.pending_turn = None

    def set_focused_object(self, focused_object: FocusedObject):
        self.focused_object = focused_object

