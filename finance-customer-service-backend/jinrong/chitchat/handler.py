from jinrong.chitchat.responder import ChitchatResponder
from jinrong.domain.state import DialogueState


class ChitchatHandler:
    def __init__(self,
                 chitchat_responder: ChitchatResponder):
        self.chitchat_responder = chitchat_responder

    async def handle(self,
                     chitchat: str,
                     dialogue_state: DialogueState):
        bot_message = await self.chitchat_responder.respond(chitchat, dialogue_state)

        return bot_message
