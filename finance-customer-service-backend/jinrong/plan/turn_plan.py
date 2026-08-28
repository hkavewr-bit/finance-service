from dataclasses import dataclass
from enum import Enum
from typing import Any

from jinrong import knowledge
from jinrong.task.commands.command import Command


@dataclass(slots=True)
class TaskTurnPlan:
    commands: list[Command]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'TaskTurnPlan':
        return cls(commands=[Command.from_dict(cmd) for cmd in data['commands']])


@dataclass(slots=True)
class KnowledgeTurnPlan:
    intents: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'KnowledgeTurnPlan':
        return cls(intents=[intent for intent in data['intents']])


@dataclass(slots=True)
class ChitchatTurnPlan:
    chat: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ChitchatTurnPlan':
        return cls(chat=data.get('chat'))


@dataclass(slots=True)
class TurnPlan:
    task: TaskTurnPlan | None = None
    knowledge: KnowledgeTurnPlan | None = None
    chitchat: ChitchatTurnPlan | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'TurnPlan':
        return cls(
            task=TaskTurnPlan.from_dict(data['task']) if data.get('task') else None,
            knowledge=KnowledgeTurnPlan.from_dict(data['knowledge']) if data.get('knowledge') else None,
            chitchat=ChitchatTurnPlan.from_dict(data['chitchat']) if data.get('chitchat') else None,

        )

    def activated_tracks(self):
        activated_tracks = []

        if self.task is not None:
            activated_tracks.append("task")

        if self.knowledge is not None:
            activated_tracks.append("knowledge")

        if self.chitchat is not None:
            activated_tracks.append("chitchat")

        return activated_tracks


class ClarifyReason(Enum):
    MISSING_TRACK = "missing_track"
    MULTIPLE_TRACKS = "multiple_tracks"
    MISSING_TASK_COMMANDS = "missing_task_commands"
    MISSING_KNOWLEDGE_INTENT = "missing_knowledge_intent"
    MISSING_FOCUSED_OBJECT = "missing_focused_object"
    OBJECT_REQUIRES_INTENT = "object_requires_intent"
    INVALID_TASK_COMMANDS = "invalid_task_commands"
    MULTIPLE_TASK_FLOWS = "multiple_task_flows"
    UNKNOWN_TASK_FLOW = "unknown_task_flow"


@dataclass(slots=True)
class TurnPlanValidatedResult:
    valid: bool
    reason: ClarifyReason | None = None
