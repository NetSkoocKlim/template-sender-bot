import datetime
import inspect
import logging
from urllib.parse import quote
from typing import AsyncIterator

from fastapi import  UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi import APIRouter

from .dependencies import get_s3_client
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api')


@router.get('/s3_health')
async def s3_health(client=Depends(get_s3_client)):
    try:
        await client.head_bucket(Bucket=settings.storage.bucket_name)
        return {"ok": True}
    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }


@router.get("/buckets")
async def list_buckets(client = Depends(get_s3_client)):
    response = await client.list_buckets()
    return {"Buckets": [b["Name"] for b in response.get("Buckets", [])]}


@router.post("/upload")
async def upload_file(
        key: str = Form(...),
        file: UploadFile = File(...),
        client=Depends(get_s3_client)
):
    file_data = await file.read()
    try:
        await client.put_object(
            Bucket=settings.storage.bucket_name,
            Key=key,
            Body=file_data
        )
    except Exception as e:
        logger.exception("Ошибка при загрузке файла: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error during upload")

    return {"bucket": settings.storage.bucket_name, "key": key, "size": len(file_data)}


@router.get("/download/{key:path}")
async def download_file(key: str, client=Depends(get_s3_client)):
    logger.info("Downloading file with key: %s, from s3_storage", key)
    try:
        response = await client.get_object(Bucket=settings.storage.bucket_name, Key=key)
    except client.exceptions.NoSuchKey as e:
        logger.info("File now found", key)
        raise HTTPException(status_code=404, detail=f"Object not found: {key}")
    logger.info("File was successfully_downloaded")

    body = response["Body"]
    content_type = response.get("ContentType") or "application/octet-stream"
    content_length = response.get("ContentLength")

    timestamp = int(datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).timestamp())
    filename = f"mailing-result-{timestamp}.csv"

    ascii_name = filename.encode("ascii", "ignore").decode("ascii") or "download"
    filename_utf8_quoted = quote(filename, safe="")
    content_disposition = f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{filename_utf8_quoted}'

    headers = {"Content-Disposition": content_disposition}
    if content_length is not None:
        headers["Content-Length"] = str(content_length)

    async def stream_generator() -> AsyncIterator[bytes]:
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

    return StreamingResponse(
        stream_generator(),
        media_type=content_type,
        headers=headers
    )