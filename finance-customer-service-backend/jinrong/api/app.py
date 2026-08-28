from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from jinrong.Infrastructure import db_client
from jinrong.Infrastructure.db_client import init_db_engine, dispose_engine
from jinrong.Infrastructure.http_client import init_http_client, disposed_http_client
from jinrong.api.chat_router import router
from jinrong.repository.base import Base
from jinrong.repository.dialogue_record import DialogueRecord  # noqa: F401 确保模型注册到 metadata


async def lifespan(_: FastAPI) :
    print("Application startup")
    init_db_engine()
    # 自动建表（dialogue_record），幂等
    async with db_client.session_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    init_http_client()

    yield

    print("Application shutdown")

    await dispose_engine()
    await disposed_http_client()


app = FastAPI(description="Finance Customer Service Backend API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})