from abc import ABC, abstractmethod
from dataclasses import field, dataclass
from typing import Any

from jinrong.domain.messages import BotMessage
from jinrong.domain.state import DialogueState

@dataclass
class ActionResult:
    messages: list[BotMessage]  = field(default_factory=list)
    updated_slots : dict[str,Any] = field(default_factory=dict)


class Action(ABC):

    name: str

    @abstractmethod
    async def run(self,
                  state: DialogueState,
                  action_kwargs : dict[str,Any]) -> ActionResult:
        pass