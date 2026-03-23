from config import settings
from fastapi import Request

def get_mailing_upload_consumer(request: Request):
    return request.app.state.mailing_upload_consumer


async def get_s3_client(request: Request):
    async with request.app.state.s3_session.client(
            service_name="s3",
            endpoint_url="https://storage.yandexcloud.net",
            region_name="ru-central1",
            aws_access_key_id=settings.storage.key_id,
            aws_secret_access_key=settings.storage.secret,
    ) as client:
        yield client
