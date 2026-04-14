from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BASE_TELEGRAM_BOT_TOKEN: SecretStr = ""

    @property
    def bot_token(self):
        return self.BASE_TELEGRAM_BOT_TOKEN.get_secret_value()


    class Config:
        env_file = ".env"
        case_sensitive = True
        env_file_encoding = "utf-8"

@lru_cache(maxsize=None)
def get_settings():
    return Settings()

settings = get_settings()
