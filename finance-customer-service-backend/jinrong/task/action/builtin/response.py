from typing import Any

from jinja2 import Template
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from jinrong.Infrastructure.llm_client import llm_client
from jinrong.chat_history.builder import ChatHistoryBuilder
from jinrong.domain.messages import BotMessage
from jinrong.domain.state import DialogueState
from jinrong.task.action.base import Action, ActionResult


class ActionResponse(Action):
    name = 'action_response'

    async def run(self,
                  state: DialogueState,
                  action_kwargs: dict[str, Any]) -> ActionResult:
        mode = action_kwargs.get('mode', 'static')

        if mode == 'static':
            text = action_kwargs.get('text')
            rendered_text = self._render_text(text, state)
            return ActionResult(
                messages=[BotMessage(text=rendered_text)]
            )
        elif mode == 'rephrase':
            text = action_kwargs.get('text')
            rendered_text = self._render_text(text, state)
            prompt_text = action_kwargs['prompt']

            message = await self.call_llm(prompt_text, state, rendered_text)
            return ActionResult(messages=[BotMessage(text=message)])

        else:
            prompt_text = action_kwargs['prompt']
            message = await self.call_llm(prompt_text, state)
            return ActionResult(messages=[BotMessage(text=message)])

    def _render_text(self,
                     text: str,
                     state: DialogueState) -> str:
        template = Template(text)
        result = template.render(
            slots=state.active_task.slots if state.active_task else {},
            context=state.current_task()
        )
        return result

    async def call_llm(self,
                       prompt_text: str,
                       state: DialogueState,
                       render_text:str="") ->str:
        prompt_template = PromptTemplate.from_template(prompt_text)

        chain = prompt_template | llm_client | StrOutputParser()

        result = await chain.ainvoke({
            "history": ChatHistoryBuilder.builder(state.current_session().turns[-5:]),
            "user_message": ChatHistoryBuilder.builder_user_message_str(state.pending_turn.user_message),
            "current_response": render_text
        })

        return result