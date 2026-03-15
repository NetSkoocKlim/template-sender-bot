import io
import logging
import datetime
from contextlib import asynccontextmanager
from typing import AsyncIterator, Any, AsyncGenerator, Tuple, Dict

import inspect
from urllib.parse import quote

import aioboto3
import botocore
import uvicorn
from fastapi import  UploadFile,  HTTPException
from fastapi.responses import StreamingResponse
from config import settings

logger = logging.getLogger(__name__)

class ObjectStorageApp:
    def __init__(self):
        self.session = aioboto3.Session()
        self._client_kwargs = dict(
            service_name="s3",
            endpoint_url="https://storage.yandexcloud.net",
            region_name="ru-central1",
            aws_access_key_id=settings.storage.key_id,
            aws_secret_access_key=settings.storage.secret,
        )

    def _get_client(self):
        return self.session.client(**self._client_kwargs)

    async def get_list_of_buckets(self):
        async with self._get_client() as client:
            response = await client.list_buckets()
            return {"Buckets": [b["Name"] for b in response.get("Buckets", [])]}

    async def upload_file(self, file_data: bytes, key: str):
        async with self._get_client() as client:
            key = key
            try:
                await client.put_object(Bucket=settings.storage.bucket_name, Key=key, Body=file_data)
            except Exception as e:
                logger.exception(e)
            return {"bucket": settings.storage.bucket_name, "key": key, "size": len(file_data)}


    async def _get_object_stream(self, key: str) -> Tuple[AsyncIterator[bytes], Dict]:
        async with self._get_client() as client:
            try:
                response = await client.get_object(Bucket=settings.storage.bucket_name, Key=key)
            except client.exceptions.NoSuchKey as e:
                raise FileNotFoundError(f"Object not found: {key}") from e

            body = response["Body"]
            content_type = response.get("ContentType") or "application/octet-stream"
            content_length = response.get("ContentLength")
            filename = f"mailing-result-{int(datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).timestamp())}.csv"

            async def iterator() -> AsyncIterator[bytes]:
                try:
                    while True:
                        chunk = await body.read(64 * 1024)
                        if not chunk:
                            break
                        yield chunk
                finally:
                    aclose = getattr(body, "aclose", None)
                    close = getattr(body, "close", None)
                    try:
                        if aclose is not None:
                            maybe = aclose()
                            if inspect.isawaitable(maybe):
                                await maybe
                        elif close is not None:
                            maybe = close()
                            if inspect.isawaitable(maybe):
                                await maybe
                    except Exception:
                        logger.exception("Error closing body stream for key=%s", key)

            ascii_name = filename.encode("ascii", "ignore").decode("ascii") or "download"
            filename_utf8_quoted = quote(filename, safe="")
            content_disposition = f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{filename_utf8_quoted}'

            headers = {"Content-Disposition": content_disposition}
            if content_length is not None:
                headers["Content-Length"] = str(content_length)

            metadata = {
                "filename": filename,
                "content_type": content_type,
                "headers": headers,
                "content_length": content_length,
            }

            return iterator(), metadata


    async def download_file(self, key: str) -> Tuple[bytes, Dict]:
        stream, meta = await self._get_object_stream(key)
        buf = io.BytesIO()
        async for chunk in stream:
            buf.write(chunk)
        return buf.getvalue(), meta


