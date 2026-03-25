import logging

from shared.src.rabbitmq.publisher import RabbitPublisher
from shared.src.rabbitmq.topology_manager import RabbitTopologyManager
from shared.src.rabbitmq.routes import Routes,  Exchanges

logger = logging.getLogger(__name__)

class MailingRetrySender(RabbitPublisher):
    def __init__(
        self,
        topology_manager: RabbitTopologyManager,

    ):
        super().__init__(topology_manager)

    async def retry_upload_mailing(self, command, delay_ms: int):
        rout = Routes.retry_route(
            exchange_name=Exchanges.MAILINGS,
            base_routing_key=Routes.MAILING_UPLOAD,
            delay_ms=delay_ms,
        )
        await self._publish(
            exchange_name=rout.exchange_name,
            routing_key=rout.routing_key,
            payload=command
        )
