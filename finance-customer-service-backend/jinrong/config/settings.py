from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from jinrong.domain.messages import MessageType

PROJECT_ROOT = Path(__file__).parents[2]
ENV_FILE = PROJECT_ROOT / ".env"

class Settings(BaseSettings):
    llm_model: str
    llm_api_key: str
    llm_base_url: str
    finance_api_base_url: str
    database_url: str
    app_host: str
    app_port: int
    # 数据中台鉴权与演示身份
    channel_code: str = "MOBILE_BANK"
    operator_no: str = "EMP000006"
    demo_customer_no: str = "CUS00000001"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8"
    )


settings = Settings() #type:ignore

if __name__ == "__main__":
    print(settings.database_url)

    print(MessageType.TEXT)