from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Command:
    command: str

    @staticmethod
    def from_dict(data: dict[str, Any]) -> 'Command':
        clz = COMMAND_TO_CLASS[data['command']]
        return clz(**data)


@dataclass(slots=True)
class StartFlowCommand(Command):
    flow: str

@dataclass(slots=True)
class SetSlotsCommand(Command):
    slots: dict[str,Any] = field(default_factory=dict)


@dataclass(slots=True)
class CancelFlowCommand(Command):
    flow: str | None = None


@dataclass(slots=True)
class ResumeFlowCommand(Command):
    flow: str | None = None



COMMAND_TO_CLASS : dict[str, type[Command] ] = {
    'start_flow': StartFlowCommand,
    'cancel_flow': CancelFlowCommand,
    'resume_flow': ResumeFlowCommand,
    'set_slots': SetSlotsCommand,
}