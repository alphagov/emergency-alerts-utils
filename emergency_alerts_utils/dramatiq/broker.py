from base64 import b64decode
from time import sleep

from dramatiq.message import Message
from dramatiq_sqs.broker import SQSBroker, SQSConsumer, _SQSMessage


class EasSqsConsumer(SQSConsumer):
    def __init__(self, queue, prefetch, timeout, *, visibility_timeout=None):
        super().__init__(queue, prefetch, timeout, visibility_timeout=visibility_timeout)

        # This defaults to the worker timeout (usually 1s), which is a bit pointless
        # as we'd want the SQS request to last as long as possible to reduce charges
        self.wait_time_seconds = 20

    def __next__(self):  # noqa C901
        """
        The overridden method does not provide a way to adjust the params to the SQS receive call.
        Namely, we'd rather have the attributes/metadata about messages which can be used by our
        retry middleware (e.g. ApproximateReceiveCount) and logged.

        It also works around an infinite spin loop while enough messages are in-memory by sleeping
        before returning None.
        """

        kw = {
            "MaxNumberOfMessages": self.prefetch,
            "WaitTimeSeconds": self.wait_time_seconds,
            "MessageSystemAttributeNames": ["All"],  # The only extra kw
        }
        if self.visibility_timeout is not None:
            kw["VisibilityTimeout"] = self.visibility_timeout

        try:
            return self.messages.popleft()
        except IndexError:
            if self.message_refc < self.prefetch:
                for sqs_message in self.queue.receive_messages(**kw):
                    try:
                        encoded_message = b64decode(sqs_message.body)
                        dramatiq_message = Message.decode(encoded_message)
                        self.messages.append(_SQSMessage(sqs_message, dramatiq_message))
                        self.message_refc += 1
                    except Exception:  # pragma: no cover
                        self.logger.exception("Failed to decode message: %r", sqs_message.body)

            try:
                return self.messages.popleft()
            except IndexError:
                # If we return None this method will be called again right away, leading to a loop
                # if not self.message_refc < self.prefetch (i.e. we have enough messages).
                # Thus we should wait a bit to let the CPU not burn cycles needlessly while
                # competing against other thread(s) that are trying to process messages.
                if not self.message_refc < self.prefetch:
                    sleep(0.1)

                return None

    def nack(self, message: _SQSMessage):
        """
        The default SQSConsumer behaviour for a nack is to ...ack.
        That just throws the message away as if it succeeded and breaks the Retries middleware.
        Instead we should let SQS redeliver it by changing the visibility timeout.

        (For those not aware, nack is only called if something calls message.fail() - such as a
        retry middleware. An actor raising an exception won't nack out of the box automatically.)

        So we don't get stuck in a loop, SQS could DLQ it if configured or a middleware could
        suppress the nack and let it ack.
        """
        # message._sqs_message is https://docs.aws.amazon.com/boto3/latest/reference/services/sqs/message/#SQS.Message
        self.logger.warning("nack-ing message ID: %s (SQS: %s)", message.message_id, message._sqs_message.message_id)
        self.message_refc -= 1

        try:
            # 10s is arbitrary - but something a lot sooner than potentially a 5 minute timeout
            # defined on the queue.
            message._sqs_message.change_visibility(VisibilityTimeout=10)
        except Exception:
            self.logger.exception("Error when shortening SQS visibility (is it about to be redelivered anyway?)")


class EasSqsBroker(SQSBroker):
    @property
    def consumer_class(self):
        return EasSqsConsumer
