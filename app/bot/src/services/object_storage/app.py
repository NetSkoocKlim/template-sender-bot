import base64
import io
import logging
import datetime
from contextlib import asynccontextmanager
from typing import AsyncIterator, Any, AsyncGenerator, Tuple, Dict

import inspect
from urllib.parse import quote

import aiohttp

from shared.src.rabbitmq.schemas import UploadMailingCommand
from .csv_sender import MailingSender
# import aioboto3
# import botocore
# import uvicorn
# from fastapi import  UploadFile,  HTTPException
# from fastapi.responses import StreamingResponse
from config import settings

logger = logging.getLogger(__name__)

class ObjectStorage:
    def __init__(self, maling_sender: MailingSender):
        self._maling_sender = maling_sender


    async def upload_mailing_file(self, file_data: bytes, admin_id: int, mailing_id: int):
        await self._maling_sender.upload_mailing_command(
            UploadMailingCommand(
                sender_id=admin_id,
                mailing_id=mailing_id,
                file_name=f"mailing-result-{admin_id}-{mailing_id}.csv",
                file_bytes_b64=base64.b64encode(file_data).decode('utf-8'),
            )
        )


    async def download_file(self, key: str) -> Tuple[bytes, str]:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://s3_api:8000/api/download/{key}"
            ) as response:
                file_bytes = await response.read()

                cd = response.headers.get("Content-Disposition", "")
                filename = "result.csv"

                if 'filename="' in cd:
                    filename = cd.split('filename="')[1].split('"')[0]
                return file_bytes, filename
        # stream, meta = await self._get_object_stream(key)
        # buf = io.BytesIO()
        # async for chunk in stream:
        #     buf.write(chunk)
        # return buf.getvalue(), meta
        pass


