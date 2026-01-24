from pydantic import Field, BaseModel, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DBConfig(BaseModel):
    USERNAME: str = "postgres"
    PASSWORD: str = "postgres"
    HOST: str = "localhost"
    PORT: int = 5432
    NAME: str = "table"

    @computed_field()
    @property
    def URL(self) -> str:
        return f"postgresql+asyncpg://{self.USERNAME}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.NAME}"

class BotConfig(BaseModel):
    TOKEN: str = ""
    ADMIN_ID: str = ""

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="_",
        env_nested_max_split=1,
    )

    bot: BotConfig = Field(default_factory=BotConfig)
    db: DBConfig = Field(default_factory=DBConfig)

settings = Settings()
