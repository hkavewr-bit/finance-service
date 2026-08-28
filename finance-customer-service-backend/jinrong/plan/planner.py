import json
from dataclasses import dataclass, asdict
from typing import Any

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

from jinrong import knowledge
from jinrong.Infrastructure.llm_client import llm_client
from jinrong.chat_history.builder import ChatHistoryBuilder
from jinrong.domain.state import DialogueState
from jinrong.knowledge.intents import KnowledgeIntent
from jinrong.plan.turn_plan import TurnPlan
from jinrong.prompt.loader import load_prompt_template_content
from jinrong.task.flows.flows import FlowList


@dataclass(slots=True)
class TurnPlanner:
    async def predict(self,
                      dialogue_state: DialogueState,
                      *,
                      flow_list: FlowList,
                      knowledge_intents: dict[str, KnowledgeIntent],
                      ) -> TurnPlan:
        prompt_inputs: dict[str, Any] = self._build_prompt_inputs(dialogue_state, flow_list=flow_list,
                                                                  knowledge_intents=knowledge_intents)

        llm_result: TurnPlan = await self._invoke(prompt_inputs)

        return llm_result

    def _build_prompt_inputs(self, state: DialogueState, *, flow_list: FlowList,
                             knowledge_intents: dict[str, KnowledgeIntent]) -> dict[str, Any]:
        user_message_str = ChatHistoryBuilder.builder_user_message_str(state.pending_turn.user_message)
        current_conversation = ChatHistoryBuilder.builder(state.current_session().turns[-10:])
        focused_object_json = json.dumps(state.focused_object.to_dict(),
                                         ensure_ascii=False) if state.focused_object else None

        interrupted_tasks_json = json.dumps([task.to_dict() for task in state.paused_tasks], ensure_ascii=False)

        active_task_json = json.dumps(state.active_task.to_dict(), ensure_ascii=False) if state.active_task else None

        available_flows_json = json.dumps([
            {
                k: v for k, v in asdict(flow).items() if not k == 'steps'
            }
            for flow in flow_list.flows if not flow.id.startswith("system_")
        ], ensure_ascii=False
        )

        knowledge_intents_json = json.dumps([
            {
                "id": intent_id,
                "description" : knowledge_intent.description,
            } for intent_id, knowledge_intent in knowledge_intents.items()
        ], ensure_ascii=False)

        return {
            "user_message": user_message_str,
            "current_conversation": current_conversation,
            "focused_object_json": focused_object_json,
            "interrupted_tasks_json": interrupted_tasks_json,
            "active_task_json": active_task_json,
            "available_flows_json": available_flows_json,
            "knowledge_intents_json": knowledge_intents_json
        }

    async def _invoke(self, prompt_inputs: dict[str, Any]) -> TurnPlan:
        prompt_template_str = load_prompt_template_content('turn_plan')

        prompt_template = PromptTemplate.from_template(template=prompt_template_str, template_format='jinja2')

        chain = prompt_template | llm_client | JsonOutputParser()

        llm_result = await chain.ainvoke(prompt_inputs)

        return TurnPlan.from_dict(llm_result)
