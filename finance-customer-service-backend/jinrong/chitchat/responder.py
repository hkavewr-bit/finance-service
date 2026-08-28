from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from jinrong.Infrastructure.llm_client import llm_client
from jinrong.chat_history.builder import ChatHistoryBuilder
from jinrong.domain.messages import BotMessage
from jinrong.domain.state import DialogueState
from jinrong.prompt.loader import load_prompt_template_content


class ChitchatResponder:

    async def respond(self, chitchat: str, state: DialogueState):
        prompt_template_str = load_prompt_template_content("chitchat_respond")

        prompt_template = PromptTemplate.from_template(template=prompt_template_str, template_format="jinja2")

        chain = prompt_template | llm_client | StrOutputParser()

        result = await chain.ainvoke(
            {
                "user_message": chitchat,
                "history": ChatHistoryBuilder.builder(state.current_session().turns[-10:])
            }
        )

        return [BotMessage(text=result)]
