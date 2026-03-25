from dataclasses import dataclass


class Exchanges:
    MAILINGS = "mailings"


class Queues:
    MAILINGS_SAVE = "mailing.saves"

    MAILING_RESULTS = "mailing.save.results"


class RoutingKeys:
    MAILING_UPLOAD = "mailing.save"

    MAILING_RESULT = "mailing.save.result"


RETRY_DELAYS_MS = (
    30_000,
    60_000,
    120_000,
    240_000,
    480_000,
    960_000,
)

def _format_delay_suffix(delay_ms: int):
    seconds = delay_ms // 1000
    return f"{seconds}s"

def _format_retry_queue_name(base_queue_name: str, delay_ms: int):
    return f"{base_queue_name}.retry.{_format_delay_suffix(delay_ms)}"

def _format_retry_routing_key(base_routing_key_name: str, delay_ms: int):
    return f"{base_routing_key_name}.retry.{_format_delay_suffix(delay_ms)}"


@dataclass
class MessageRoute:
    exchange_name: str
    routing_key: str


@dataclass
class QueueBinding:
    exchange: str
    queue: str
    routing_key: str

    durable: bool = True
    exclusive: bool = False
    auto_delete: bool = False
    arguments: dict | None = None


class Routes:
    MAILING_UPLOAD = MessageRoute(
        exchange_name=Exchanges.MAILINGS,
        routing_key=RoutingKeys.MAILING_UPLOAD,
    )


    MAILING_RESULT = MessageRoute(
        exchange_name=Exchanges.MAILINGS,
        routing_key=RoutingKeys.MAILING_RESULT,
    )


    @staticmethod
    def retry_route(exchange_name: str, base_routing_key: str, delay_ms: int):
        return MessageRoute(
            exchange_name=exchange_name,
            routing_key=_format_retry_routing_key(
                base_routing_key,
                delay_ms
            ),
        )

class Bindings:
    MAILING_UPLOAD = QueueBinding(
        exchange=Routes.MAILING_UPLOAD.exchange_name,
        queue=Queues.MAILINGS_SAVE,
        routing_key=Routes.MAILING_UPLOAD.routing_key,
    )


    MAILING_RESULT = QueueBinding(
        exchange=Routes.MAILING_RESULT.exchange_name,
        queue=Queues.MAILING_RESULTS,
        routing_key=Routes.MAILING_RESULT.routing_key,
    )

    @staticmethod
    def retry_binding(
            exchange_name: str,
            base_queue_name: str,
            base_routing_key: str,
            delay_ms: int
    ):
        return QueueBinding(
            exchange=exchange_name,
            queue=_format_retry_queue_name(base_queue_name, delay_ms),
            routing_key=_format_retry_routing_key(base_routing_key, delay_ms),
            arguments={
                "x-message-ttl": delay_ms,
                "x-dead-letter-exchange": Exchanges.MAILINGS,
                "x-dead-letter-routing-key": RoutingKeys.MAILING_UPLOAD,
            },
        )


RETRY_MAILING_BINDINGS = [
    Bindings.retry_binding(
        exchange_name=Exchanges.MAILINGS,
        base_routing_key=RoutingKeys.MAILING_UPLOAD,
        base_queue_name=Queues.MAILINGS_SAVE,
        delay_ms=delay
    ) for delay in RETRY_DELAYS_MS
]

ALL_BINDINGS = (
    Bindings.MAILING_UPLOAD,
    *RETRY_MAILING_BINDINGS,
    Bindings.MAILING_RESULT,
)