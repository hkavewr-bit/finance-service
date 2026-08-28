from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from jinrong.Infrastructure.llm_client import llm_client
from jinrong.chat_history.builder import ChatHistoryBuilder
from jinrong.domain.messages import BotMessage
from jinrong.domain.state import DialogueState
from jinrong.knowledge.provider.provider import KnowledgeChunk
from jinrong.prompt.loader import load_prompt_template_content


class KnowledgeResponder:

    async def respond(self,
                      knowledge_chunks : list[KnowledgeChunk],
                      state: DialogueState) -> list[BotMessage]:
        prompt_template_str = load_prompt_template_content("knowledge_respond")

        prompt_template= PromptTemplate.from_template(template=prompt_template_str,template_format="jinja2")

        chain = prompt_template | llm_client | StrOutputParser()


        result = await chain.ainvoke({
            "user_message": ChatHistoryBuilder.builder_user_message_str(state.pending_turn.user_message),
            "history": ChatHistoryBuilder.builder(state.current_session().turns[-10:]),
            "knowledge_content": "\n\n".join([chunk.content for chunk in knowledge_chunks])
        })

        return [BotMessage(text = result)]
