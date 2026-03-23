from dataclasses import dataclass

class Exchanges:
    MAILINGS = 'mailings'


class Queues:
    MAILINGS_SAVE = 'mailing.saves'
    MAILING_RESULTS = 'mailing.save.results'

class RoutingKeys:
    MAILING_UPLOAD = "mailing.save"
    MAILING_RESULT = "mailing.save.result"


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



class Routes:
    MAILING_UPLOAD = MessageRoute(
        exchange_name=Exchanges.MAILINGS,
        routing_key=RoutingKeys.MAILING_UPLOAD,
    )

    MAILING_RESULT = MessageRoute(
        exchange_name=Exchanges.MAILINGS,
        routing_key=RoutingKeys.MAILING_RESULT,
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

    ALL = (
        MAILING_UPLOAD,
        MAILING_RESULT
    )