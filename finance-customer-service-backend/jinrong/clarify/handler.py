import json

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from jinrong.Infrastructure.llm_client import llm_client
from jinrong.chat_history.builder import ChatHistoryBuilder
from jinrong.domain.messages import BotMessage
from jinrong.domain.state import DialogueState
from jinrong.plan.turn_plan import ClarifyReason
from jinrong.prompt.loader import load_prompt_template_content


class ClarifyResponder:
    async def respond(self,
                      reason: ClarifyReason,
                      dialogue_state: DialogueState):
        prompt_inputs = self._build_prompt_inputs(reason, dialogue_state)

        rewritten = await self._invoke(prompt_inputs)

        return rewritten

    def _build_prompt_inputs(self,
                             reason: ClarifyReason,
                             dialogue_state: DialogueState):
        user_message_str = ChatHistoryBuilder.builder_user_message_str(dialogue_state.pending_turn.user_message)
        history_str = ChatHistoryBuilder.builder(dialogue_state.current_session().turns[-10:])

        focused_object_json = json.dumps(
            dialogue_state.focused_object.to_dict(),
            ensure_ascii=False
        ) if dialogue_state.focused_object else None

        clarify_message_str = self.build_clarify_message(reason, dialogue_state)

        return {
            "user_message": user_message_str,
            "history": history_str,
            "focused_object": focused_object_json,
            "clarify_message": clarify_message_str,
            "reason": reason.value,
        }

    def build_clarify_message(
            self,
            reason: ClarifyReason,
            state: DialogueState,
    ) -> str:
        if reason is ClarifyReason.MULTIPLE_TRACKS:
            return "你这次同时提到了多个方向。我们先处理一个，你想先办业务还是先咨询信息呢？"

        if reason is ClarifyReason.MISSING_FOCUSED_OBJECT:
            return "请先发送你想咨询的对象，我再继续帮你看。"

        if reason is ClarifyReason.MISSING_KNOWLEDGE_INTENT:
            return "你是想了解账户信息、银行卡信息、交易流水，还是贷款或理财产品信息呢？"

        if reason is ClarifyReason.MISSING_TRACK:
            return "你是想先办理业务，还是先咨询信息呢？"

        if reason is ClarifyReason.MISSING_TASK_COMMANDS:
            return "你这次是想办理什么业务呢？比如查账户余额、查交易流水、申请贷款、挂失银行卡，或者提交投诉。"

        if reason is ClarifyReason.OBJECT_REQUIRES_INTENT:
            focused_object = state.focused_object
            if focused_object is not None and focused_object.type == "account":
                return "我已经收到这个账户了。你想查余额、查交易流水，还是了解账户状态呢？"
            if focused_object is not None and focused_object.type == "card":
                return "我已经收到这张银行卡了。你想了解它的卡信息，还是办理挂失呢？"
            if focused_object is not None and focused_object.type == "loan_product":
                return "我已经收到这个贷款产品了。你想了解它的额度、期限还是利率呢？"
            if focused_object is not None and focused_object.type == "wealth_product":
                return "我已经收到这个理财产品了。你想了解它的起购金额、收益率还是风险等级呢？"

        return "我还需要再确认一下你的意思，你可以换个更具体的说法告诉我。"

    async def _invoke(self, prompt_inputs):
        prompt_template_str  = load_prompt_template_content("clarify_respond")

        prompt_template = PromptTemplate.from_template(prompt_template_str , template_format="jinja2")

        chain  = prompt_template | llm_client | StrOutputParser()

        rewritten = await chain.ainvoke(prompt_inputs)

        return [BotMessage(rewritten)]
