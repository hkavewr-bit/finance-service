from jinrong.domain.state import DialogueState
from jinrong.knowledge.intents import KnowledgeIntent
from jinrong.knowledge.provider.register import KnowledgeRegister
from jinrong.knowledge.responder import KnowledgeResponder


class KnowledgeHandler:
    def __init__(self,
                 knowledge_intents: dict[str, KnowledgeIntent],
                 knowledge_register: KnowledgeRegister,
                 knowledge_responder: KnowledgeResponder):
        self.knowledge_intents = knowledge_intents
        self.knowledge_register = knowledge_register
        self.knowledge_responder = knowledge_responder

    async def handle(self, intents: list[str], dialogue_state: DialogueState):

        provider_ids = self._get_provider_ids_by_intents(intents)

        final_chunks = []

        for provider_id in provider_ids:
            provider = self.knowledge_register.get_provider_by_id(provider_id)
            knowledge_chunks = await provider.retrival(state=dialogue_state)
            final_chunks.extend(knowledge_chunks)

        bot_message = await self.knowledge_responder.respond(final_chunks,state=dialogue_state)

        return bot_message

    def _get_provider_ids_by_intents(self, intents: list[str]) -> list[str]:

        final_providers = []

        for intent in intents:
            knowledge_intent_obj = self.knowledge_intents.get(intent)

            final_providers.extend(knowledge_intent_obj.provider_ids)

        return list(set(final_providers))
