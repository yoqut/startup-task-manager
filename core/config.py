from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BASE_TELEGRAM_BOT_TOKEN: SecretStr = ""
    TELEGRAM_WEBHOOK_URL: SecretStr = ""

    @property
    def bot_token(self):
        return self.BASE_TELEGRAM_BOT_TOKEN.get_secret_value()


    @property
    def webhook_url(self):
        return self.TELEGRAM_WEBHOOK_URL.get_secret_value()

    @property
    def allow_hosts(self):
        return [self.webhook_url, "127.0.0.1"]

    class Config:
        env_file = ".env"
        case_sensitive = True
        env_file_encoding = "utf-8"

@lru_cache(maxsize=None)
def get_settings():
    return Settings()

settings = get_settings()
