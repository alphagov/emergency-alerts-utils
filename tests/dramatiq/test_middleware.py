from unittest.mock import Mock

import pytest

from emergency_alerts_utils.dramatiq.middleware import (
    ActorQueuePrefixMiddleware,
    SqsRetryMiddleware,
)


def test_actors_have_queue_names_prefixed():
    mock_actor = Mock()
    mock_actor.options = {}
    mock_actor.queue_name = "queue"

    middleware = ActorQueuePrefixMiddleware(prefix="test-")
    middleware.before_declare_actor(None, mock_actor)

    assert mock_actor.queue_name == "test-queue"
    assert mock_actor.options["original_queue_name"] == "queue"


def test_actors_cant_get_prefixed_twice():
    mock_actor = Mock()
    mock_actor.options = {}
    mock_actor.queue_name = "queue"

    middleware = ActorQueuePrefixMiddleware(prefix="test-")
    middleware.before_declare_actor(None, mock_actor)
    middleware.before_declare_actor(None, mock_actor)

    assert mock_actor.queue_name == "test-queue"
    assert mock_actor.options["original_queue_name"] == "queue"


@pytest.mark.parametrize("allow_retry", [False, True])
def test_retry_middleware_ignores_messages_without_an_exception(allow_retry):
    mock_message = Mock()
    mock_broker = Mock()
    mock_actor = Mock()
    mock_actor.options = {"allow_retry": allow_retry}

    mock_broker.get_actor.return_value = mock_actor

    middleware = SqsRetryMiddleware()
    middleware.after_process_message(mock_broker, mock_message, exception=None)

    mock_message.fail.assert_not_called()


def test_retry_middleware_ignores_messages_with_exception_if_not_allow_retry():
    mock_message = Mock()
    mock_broker = Mock()
    mock_actor = Mock()
    mock_actor.options = {}

    mock_broker.get_actor.return_value = mock_actor

    middleware = SqsRetryMiddleware()
    middleware.after_process_message(mock_broker, mock_message, exception=Exception("test"))

    mock_message.fail.assert_not_called()


def test_retry_middleware_fails_message_for_exception_when_allow_retry():
    mock_message = Mock()
    mock_broker = Mock()
    mock_actor = Mock()
    mock_actor.options = {"allow_retry": True}

    mock_broker.get_actor.return_value = mock_actor

    middleware = SqsRetryMiddleware()
    middleware.after_process_message(mock_broker, mock_message, exception=Exception("test"))

    mock_message.fail.assert_called_once()


def test_retry_middleware_fails_message_for_specific_exceptions_only():
    mock_message = Mock()
    mock_broker = Mock()
    mock_actor = Mock()

    class SpecificException(Exception):
        pass

    mock_actor.options = {"allow_retry": True, "retry_for": SpecificException}

    mock_broker.get_actor.return_value = mock_actor

    middleware = SqsRetryMiddleware()

    middleware.after_process_message(mock_broker, mock_message, exception=Exception("test"))
    mock_message.fail.assert_not_called()

    middleware.after_process_message(mock_broker, mock_message, exception=SpecificException("test"))
    mock_message.fail.assert_called_once()
