import datetime
from contextlib import asynccontextmanager
from typing import AsyncIterator

import inspect
from urllib.parse import quote

import aioboto3
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse
from config import settings


@asynccontextmanager
async def lifespan(app_: FastAPI):
    session = aioboto3.Session()
    client_cm = session.client(
        "s3",
        endpoint_url="https://storage.yandexcloud.net",
        region_name="ru-central1",
        aws_access_key_id=settings.storage.key_id,
        aws_secret_access_key=settings.storage.secret,
    )
    app_.state.s3_client_cm_ = client_cm
    app_.state.s3_client = await client_cm.__aenter__()
    yield
    try:
        await app_.state.s3_client_cm_.__aexit__(None, None, None)
    except Exception:
        pass

app = FastAPI(prefix="/api", lifespan=lifespan)


@app.get("/buckets")
async def list_buckets():
    client = app.state.s3_client
    resp = await client.list_buckets()
    return {"Buckets": [b["Name"] for b in resp.get("Buckets", [])]}

@app.post("/buckets")
async def upload_file(file: UploadFile = File(...),
                      key: str | None = Form(None)):
    client = app.state.s3_client
    key = key or file.filename
    body = await file.read()
    try:
        await client.put_object(Bucket=settings.storage.bucket_name, Key=key, Body=body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"bucket": settings.storage.bucket_name, "key": key, "size": len(body)}


@app.get("/download/{key}")
async def download_file(key: str):
    client = app.state.s3_client
    try:
        resp = await client.get_object(Bucket=settings.storage.bucket_name, Key=key)
    except client.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail="Not found")

    body = resp["Body"]
    content_type = resp.get("ContentType")
    filename = f"mailing-result-{int(datetime.datetime.now(datetime.timezone.utc)
                                       .replace(microsecond=0).timestamp())}.csv"

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
            if aclose is not None:
                maybe = aclose()
                if inspect.isawaitable(maybe):
                    await maybe
            elif close is not None:
                maybe = close()
                if inspect.isawaitable(maybe):
                    await maybe

    ascii_name = filename.encode('ascii', 'ignore').decode('ascii') or "download"
    filename_utf8_quoted = quote(filename, safe='')
    content_disposition = f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{filename_utf8_quoted}'
    headers = {
        "Content-Disposition": content_disposition,
    }
    content_length = resp.get("ContentLength")
    if content_length is not None:
        headers["Content-Length"] = str(content_length)
    return StreamingResponse(iterator(), media_type=content_type, headers=headers)


@app.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("services.object_storage_app.app:app", port=8004, reload=True)


