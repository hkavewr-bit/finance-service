from sqlalchemy import String, TEXT
from sqlalchemy.orm import Mapped, mapped_column

from jinrong.repository.base import Base


class DialogueRecord(Base):
    __tablename__ = 'dialogue_record'

    sender_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    state_json: Mapped[str] = mapped_column(TEXT, nullable=False, default="{}")
