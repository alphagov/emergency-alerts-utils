from dramatiq.middleware import Callbacks, ShutdownNotifications, TimeLimit
from flask_dramatiq import AppContextMiddleware, Dramatiq
from periodiq import PeriodiqMiddleware

from emergency_alerts_utils.dramatiq.broker import EasSqsBroker
from emergency_alerts_utils.dramatiq.middleware import (
    ActorQueuePrefixMiddleware,
    SqsRetryMiddleware,
)


class EasSqsFlaskDramatiq(Dramatiq):
    """
    An extension of flask_dramatiq that embraces the lazy actor mechanism, but allows compatibility
    with the SqsBroker with an opionated config.
    """

    DEFAULT_BROKER = "dramatiq.brokers.stub:StubBroker"

    def __init__(self, app=None, broker_cls=DEFAULT_BROKER, name="dramatiq", config_prefix=None, middleware=None):
        super().__init__(app, broker_cls, name, config_prefix, middleware)

        # Add middleware which provide actor options, as otherwise Dramatiq will error
        # when the stub broker initialises before we replace it with EasSqsBroker.
        self.middleware = [PeriodiqMiddleware(), SqsRetryMiddleware()]

    def init_app(self, app, queue_prefix: str):
        # flask_dramatiq provides its own @dramatiq.actor decorator
        # This has the excellent property of lazily registering so we don't actually need dramatiq
        # configured during module import. Awesome. And auto-injecting the Flask context.
        # Except asking flask_dramatiq to init doesn't give you control of the dramatiq Broker class
        # to the extent needed - only the `url` kwarg. The SQS broker doesn't use that :(

        # So we cheat here: let flask_dramatiq do its thing and then replace the stub broker instance
        # inside to what we want.
        super().init_app(app)

        middleware = [
            AppContextMiddleware(app),
            PeriodiqMiddleware(skip_delay=300),
            ActorQueuePrefixMiddleware(prefix=queue_prefix),
            SqsRetryMiddleware(),
            # This is mostly the default_middleware - except we remove Prometheus, Retries, and AgeLimit
            TimeLimit(),
            ShutdownNotifications(),
            Callbacks(),
        ]
        sqs_broker = EasSqsBroker(
            middleware=middleware,
            visibility_timeout=None,  # Use the queue's default
        )

        self.broker = sqs_broker
        for actor in self.actors:
            # Re-register the actors so they reference our new broker
            actor.register(broker=sqs_broker)
