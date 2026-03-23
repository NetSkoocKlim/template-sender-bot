from datetime import datetime, UTC

from pydantic import BaseModel, Field


class BaseMessageModel(BaseModel):
    # message_id: str
    send_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MailingMessageModel(BaseMessageModel):
    sender_id: int
    mailing_id: int
    file_name: str



class UploadMailingCommand(MailingMessageModel):
    file_bytes_b64: str
    content_type: str = "text/csv"

    attempt: int = 1


class MailingUploadResultEvent(MailingMessageModel):
    s3_key: str | None = None

    error_message: str | None = None



