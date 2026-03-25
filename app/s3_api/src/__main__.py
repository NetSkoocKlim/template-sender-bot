import logging
from contextlib import asynccontextmanager

import aioboto3
import uvicorn

from app.s3_api.src.mailing_result_sender import MailingResultSender
from app.s3_api.src.mailing_retry_sender import MailingRetrySender
from app.s3_api.src.mailing_upload_consumer import MailingUploadConsumer
from shared.src.rabbitmq.setup import init_rabbit_connection, close_rabbit_connection, get_topology_manager
from .routes import router as main_router
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

@asynccontextmanager
async def lifespan(
        app_: FastAPI,
):
    session = aioboto3.Session()
    app_.state.s3_session = session
    await init_rabbit_connection()

    mailing_result_publisher = MailingResultSender(
        get_topology_manager()
    )
    mailing_retry_publisher = MailingRetrySender(
        get_topology_manager()
    )
    mailing_upload_consumer = MailingUploadConsumer(
        get_topology_manager(),
        mailing_result_publisher,
        mailing_retry_publisher
    )
    app_.state.mailing_upload_consumer = mailing_upload_consumer
    await mailing_upload_consumer.start()
    yield
    await close_rabbit_connection()


app = FastAPI(
    lifespan=lifespan,
)
app.include_router(
    main_router
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)