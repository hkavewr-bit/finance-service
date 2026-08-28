from jinrong.chat_history.builder import ChatHistoryBuilder
from jinrong.domain.messages import UserMessage, ProcessedResult, ChatHistoryMessage
from jinrong.engines.dialogue_engine import DialogueEngine
from jinrong.repository.dialogue_repository import DialogueRepository


class DialogueStateService:
    def __init__(self,engine: DialogueEngine,repository: DialogueRepository):
        self._engine = engine
        self._repository = repository


    async def process_message(self,user_message: UserMessage) ->ProcessedResult:


        dialogue_state =await self._repository.load_state(user_message.sender_id)


        processed_result = await self._engine.handle_message(user_message,dialogue_state)


        await self._repository.save_state(user_message.sender_id,dialogue_state)


        return processed_result

    async def get_chat_history(self,sender_id : str) -> list[ChatHistoryMessage]:

        state = await self._repository.load_state(sender_id)

        final_chat_history_messages = []

        for session in state.sessions:
            for turn in session.turns:
                user_message = turn.user_message

                user_chat_history_message = ChatHistoryBuilder.build_chat_history(session.session_id,
                                                                                  "user",
                                                                                  user_message.text,
                                                                                  user_message.object)

                final_chat_history_messages.append(user_chat_history_message)

                for bot_message in turn.bot_messages:
                    bot_chat_history_message = ChatHistoryBuilder.build_chat_history(session.session_id,
                                                                                     "bot",
                                                                                     bot_message.text,
                                                                                     bot_message.object)

                    final_chat_history_messages.append(bot_chat_history_message)

        return final_chat_history_messages

    async def create_session(self, sender_id: str) -> dict:
        """新建会话：关闭当前会话、重置运行时状态、开启一个全新会话并持久化。"""
        state = await self._repository.load_state(sender_id)

        if state.current_session() is not None:
            state.close_current_session()

        state.reset_runtime_state_for_new_session()
        state.start_session()

        await self._repository.save_state(sender_id, state)

        return {"sender_id": sender_id, "session_id": state.current_session_id}

    async def get_state(self, sender_id: str) -> dict:
        """返回当前对话状态的概要（供前端恢复上下文 / 展示当前任务）。"""
        state = await self._repository.load_state(sender_id)

        return {
            "sender_id": sender_id,
            "active_task": state.active_task.to_dict() if state.active_task else None,
            "active_system_task": state.active_system_task.to_dict() if state.active_system_task else None,
            "paused_tasks": [task.to_dict() for task in state.paused_tasks],
            "focused_object": state.focused_object.to_dict() if state.focused_object else None,
            "session_count": len(state.sessions),
            "current_session_id": state.current_session_id,
        }

    async def delete_session(self, sender_id: str) -> dict:
        """清空会话：删除持久化的对话状态，下次消息从空白状态开始。"""
        await self._repository.delete_state(sender_id)

        return {"sender_id": sender_id, "status": "deleted"}
