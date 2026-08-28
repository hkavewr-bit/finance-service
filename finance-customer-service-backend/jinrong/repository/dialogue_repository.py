import json

from sqlalchemy import delete, select
from sqlalchemy.dialects.mysql import insert

from jinrong.domain.state import DialogueState
from jinrong.repository.dialogue_record import DialogueRecord


class DialogueRepository:

    def __init__(self,session):
        self._session = session


    async def load_state(self,sender_id:str)-> DialogueState:

        stmt = select(DialogueRecord).where(DialogueRecord.sender_id == sender_id)

        cursor_result = await self._session.execute(stmt)

        dialogue_record  = cursor_result.scalar_one_or_none()

        if dialogue_record is None:
            return DialogueState(sender_id=sender_id)

        dialogue_record_dict = json.loads(dialogue_record.state_json)

        return DialogueState.from_dict(dialogue_record_dict)

    async def save_state(self, sender_id, dialogue_state: DialogueState):
        dialogue_state_dict=dialogue_state.to_dict()

        dialogue_state_str=json.dumps(dialogue_state_dict,ensure_ascii=False)

        insert_stmt = insert(DialogueRecord).values(sender_id=sender_id,state_json=dialogue_state_str)

        update_stmt = insert_stmt.on_duplicate_key_update(state_json=insert_stmt.inserted.state_json)

        await self._session.execute(update_stmt)

        await self._session.commit()

    async def delete_state(self, sender_id: str):
        stmt = delete(DialogueRecord).where(DialogueRecord.sender_id == sender_id)

        await self._session.execute(stmt)

        await self._session.commit()



