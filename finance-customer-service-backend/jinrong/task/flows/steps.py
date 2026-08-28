from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from jinrong.task.flows.links import (
    FlowStepConditionLink,
    FlowStepFallbackLink,
    FlowStepLink,
    FlowStepStaticLink,
)


class FlowStepType(Enum):
    START = "start"
    END = "end"
    ACTION = "action"
    COLLECT = "collect"


@dataclass(slots=True)
class ResponseDefinition:
    text: str
    mode: str = 'static'
    prompt: str | None = None


@dataclass(slots=True)
class Validated:
    condition: str
    failure_response: ResponseDefinition | None = None


@dataclass(slots=True)
class FlowStep:
    id: str
    type: FlowStepType
    next: list[FlowStepLink]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'FlowStep':
        clz = FLOW_STEP_TO_CLASS[data['type']]

        return clz.from_dict(data)

    @staticmethod
    def load_base_fields(data: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": data['id'],
            "type": FlowStepType(data['type']),
            "next": FlowStep.load_step_next(data['next'])
        }

    @staticmethod
    def load_step_next(links: str | list[dict[str, Any]]) -> list[FlowStepLink]:
        loaded_links: list[FlowStepLink] = []
        if isinstance(links, str):
            loaded_links.append(FlowStepStaticLink(links))
        else:
            for link in links:
                if 'if' in link:
                    loaded_links.append(FlowStepConditionLink(
                        target=link['then'],
                        condition=link['if']
                    ))
                else:
                    loaded_links.append(FlowStepFallbackLink(link['else']))

        return loaded_links


@dataclass(slots=True)
class StartFlowStep(FlowStep):

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'StartFlowStep':
        return cls(**FlowStep.load_base_fields(data))


@dataclass(slots=True)
class EndFlowStep(FlowStep):

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'EndFlowStep':
        return cls(**FlowStep.load_base_fields(data))


@dataclass(slots=True)
class CollectFlowStep(FlowStep):
    slot_name: str
    response: ResponseDefinition
    validated: Validated | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'CollectFlowStep':
        return cls(
            **FlowStep.load_base_fields(data),
            slot_name=data['slot_name'],
            response=ResponseDefinition(
                text=data['response']['text'],
                mode=data['response'].get('mode', 'static'),
                prompt=data['response'].get('prompt')
            ),
            validated=Validated(
                condition=data['validated']['condition'],
                failure_response=ResponseDefinition(
                    text=data['validated']['failure_response']['text'],
                    mode=data['validated']['failure_response'].get('mode', 'static'),
                    prompt=data['validated']['failure_response'].get('prompt')
                ) if data['validated'].get('failure_response') else None
            ) if data.get('validated') else None
        )


@dataclass(slots=True)
class ActionFlowStep(FlowStep):
    action: str
    args: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ActionFlowStep':
        return cls(
            **FlowStep.load_base_fields(data),
            action= data['action'],
            args = data.get('args',{})
        )


FLOW_STEP_TO_CLASS: dict[str, type[FlowStep]] = {
    "start": StartFlowStep,
    "end": EndFlowStep,
    "collect": CollectFlowStep,
    "action": ActionFlowStep
}
