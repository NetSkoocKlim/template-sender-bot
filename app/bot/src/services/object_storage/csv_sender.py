import logging

from shared.src.rabbitmq.publisher import RabbitPublisher
from shared.src.rabbitmq.schemas import UploadMailingCommand
from shared.src.rabbitmq.topology_manager import RabbitTopologyManager
from shared.src.rabbitmq.routes import Routes

logger = logging.getLogger(__name__)

class MailingSender(RabbitPublisher):
    def __init__(
        self,
        topology_manager: RabbitTopologyManager,
    ):
        super().__init__(topology_manager)
        logger.info("Successfully Initialized topology manager for MailingSender %r", topology_manager)


    async def upload_mailing_command(self, command: UploadMailingCommand):
        rout = Routes.MAILING_UPLOAD
        await self._publish(
            exchange_name=rout.exchange_name,
            routing_key=rout.routing_key,
            payload=command
        )