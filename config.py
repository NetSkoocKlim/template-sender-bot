from dotenv import load_dotenv
from pydantic import Field, BaseModel, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

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

class RedisConfig(BaseModel):
    HOST: str = "localhost"
    PORT: int = 6379
    db: int = 0

    @computed_field()
    @property
    def URL(self) -> str:
        return f"redis://{self.HOST}:{self.PORT}/{self.db}"

class BotConfig(BaseModel):
    TOKEN: str = ""
    SUPERADMIN_ID: str = ""
    admin_secret: str = Field(default="AiVK0AT")


class StorageConfig(BaseModel):
    key_id: str = ""
    secret: str = ""
    bucket_name: str = ""


class RabitMqConfig(BaseModel):
    password: str = ""
    host: str = ""

    @computed_field()
    @property
    def url(self) -> str:
        return f"ampq://admin:{self.password}@{self.host}:5672/"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="_",
        env_nested_max_split=1,
        case_sensitive=False,
    )

    bot: BotConfig = Field(default_factory=BotConfig)
    db: DBConfig = Field(default_factory=DBConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    rabbitmq: RabitMqConfig = Field(default_factory=RabitMqConfig)


settings = Settings()


