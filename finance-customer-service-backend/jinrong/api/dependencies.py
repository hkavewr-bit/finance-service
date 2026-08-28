from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from jinrong.Infrastructure import db_client
from jinrong.engines.builder import build_dialogue_engine
from jinrong.engines.dialogue_engine import DialogueEngine
from jinrong.repository.dialogue_repository import DialogueRepository
from jinrong.services.dialogue_service import DialogueStateService


def get_dialogue_engine():
    return build_dialogue_engine()


DialogueEngineDep =  Annotated[DialogueEngine, Depends(get_dialogue_engine)]


async def get_session():
    async with db_client.session_factory() as session:
        yield session

DialogueSessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_dialogue_repository(session: DialogueSessionDep):
    return DialogueRepository(session)

DialogueRepositoryDep = Annotated[DialogueRepository, Depends(get_dialogue_repository)]



def get_dialogue_service(engine: DialogueEngineDep, repository: DialogueRepositoryDep):
    return DialogueStateService(engine, repository)


DialogueStateServiceSep = Annotated[DialogueStateService, Depends(get_dialogue_service)]
