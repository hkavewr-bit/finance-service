from typing import Literal

from jinrong.domain.messages import MessageType, UserMessage, FocusedObject, BotMessage, ChatHistoryMessage
from jinrong.domain.state import Turn


class ChatHistoryBuilder:

    @staticmethod
    def builder(turns:list[Turn]):
        chat_history = []

        for turn in turns:
            user_message_str = ChatHistoryBuilder.builder_user_message_str(turn.user_message)
            chat_history.append(f'USER:{user_message_str}')

            for bot_message in turn.bot_messages:
                bot_message_str = ChatHistoryBuilder.builder_bot_message_str(bot_message)
                chat_history.append(f'BOT:{bot_message_str}')

        return '\n'.join(chat_history)

    @classmethod
    def builder_user_message_str(cls, user_message:UserMessage) :
        if user_message.type is MessageType.TEXT:

            return cls._render_text_message(user_message.text)

        return cls._render_object_message(user_message.object)

    @classmethod
    def builder_bot_message_str(cls, bot_message: BotMessage) -> str:
        if  bot_message.object is not None:
            return  cls._render_object_message(bot_message.object)

        return  cls._render_text_message(bot_message.text)

    @classmethod
    def _render_text_message(cls, text:str):
        return text.strip()

    _OBJECT_LABELS = {
        "account": "账户",
        "card": "银行卡",
        "loan_product": "贷款产品",
        "wealth_product": "理财产品",
        "ticket": "工单",
        "order": "订单",
        "product": "商品",
    }

    @classmethod
    def _render_object_message(cls, object:FocusedObject):
        id = object.id

        label = cls._OBJECT_LABELS.get(object.type, "对象")
        title = object.title
        attributes_str = "".join([f'{k}={v}' for k,v in object.attributes.items()])

        return f"【id={id} | label={label} | title={title} | attributes={attributes_str}】"

    @classmethod
    def build_chat_history(cls,
                           session_id: str,
                           role: Literal["user", "bot"],
                           text: str,
                           object: FocusedObject) -> ChatHistoryMessage:
        return ChatHistoryMessage(
            session_id=session_id,
            role=role,
            text=text,
            object=object
        )
