from dramatiq.middleware import Callbacks, ShutdownNotifications, TimeLimit
from flask import Flask
from flask_dramatiq import AppContextMiddleware
from periodiq import PeriodiqMiddleware

from emergency_alerts_utils.dramatiq import EasSqsFlaskDramatiq
from emergency_alerts_utils.dramatiq.broker import EasSqsBroker
from emergency_alerts_utils.dramatiq.middleware import (
    ActorQueuePrefixMiddleware,
    SqsRetryMiddleware,
)


def test_init_app_binds_actor_to_sqs_broker(mocked_aws, mocker):
    dramatiq_instance = EasSqsFlaskDramatiq()
    flask_app = Flask("test")

    @dramatiq_instance.actor
    def test_actor():
        pass

    # LazyActor isn't registered at this point
    assert test_actor.actor is None

    dramatiq_instance.init_app(flask_app, "test-prefix")

    assert isinstance(test_actor.actor.broker, EasSqsBroker)


def test_init_app_registers_broker_with_middleware(mocked_aws, mocker):
    dramatiq_instance = EasSqsFlaskDramatiq()
    flask_app = Flask("test")

    dramatiq_instance.init_app(flask_app, "test-prefix")

    assert isinstance(dramatiq_instance.broker.middleware[0], AppContextMiddleware)
    assert isinstance(dramatiq_instance.broker.middleware[1], PeriodiqMiddleware)
    assert isinstance(dramatiq_instance.broker.middleware[2], ActorQueuePrefixMiddleware)
    assert dramatiq_instance.broker.middleware[2].prefix == "test-prefix"
    assert isinstance(dramatiq_instance.broker.middleware[3], SqsRetryMiddleware)
    assert isinstance(dramatiq_instance.broker.middleware[4], TimeLimit)
    assert isinstance(dramatiq_instance.broker.middleware[5], ShutdownNotifications)
    assert isinstance(dramatiq_instance.broker.middleware[6], Callbacks)
