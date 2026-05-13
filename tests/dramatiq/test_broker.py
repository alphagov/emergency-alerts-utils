from unittest.mock import Mock

import pytest

from emergency_alerts_utils.dramatiq.broker import EasSqsConsumer


def test_eas_consumer_uses_long_polling_and_attributes():
    """
    The upstream consumer uses a silly 1s poll, this increases SQS charges.
    We use the max time supported by SQS (20s)

    It also doesn't request any message metadata, such as the number of times a message has been
    received which can be useful to log.
    """

    mock_queue = Mock()
    mock_receive: Mock = mock_queue.receive_messages
    mock_receive.return_value = []

    consumer = EasSqsConsumer(mock_queue, 1, 1)

    consumer.__next__()

    mock_receive.assert_called_once_with(MaxNumberOfMessages=1, WaitTimeSeconds=20, MessageSystemAttributeNames=["All"])


@pytest.mark.parametrize("should_throw", [False, True])
def test_nack_changes_message_visibility(should_throw):
    """
    The default behaviour is just to ack (DeleteMessage). Instead we ask SQS to deliver it again but soon.
    """

    mock_message = Mock()
    # message is a dramatiq_sqs _SQSMessage
    # _sqs_message within is a boto3 resource
    # See https://docs.aws.amazon.com/boto3/latest/reference/services/sqs/message/#SQS.Message
    mock_change_visibility: Mock = mock_message._sqs_message.change_visibility

    if should_throw:
        mock_change_visibility.side_effect = Exception("AWS")

    consumer = EasSqsConsumer(None, 1, 1)
    consumer.message_refc = 1

    consumer.nack(mock_message)

    assert consumer.message_refc == 0
    mock_change_visibility.assert_called_once_with(VisibilityTimeout=10)
