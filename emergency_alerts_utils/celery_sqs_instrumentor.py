import logging
from typing import Collection

import kombu.asynchronous.aws.sqs.connection
from opentelemetry.instrumentation.celery.package import _instruments
from opentelemetry.instrumentation.celery.version import __version__
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.trace import SpanKind, get_tracer
from wrapt import wrap_function_wrapper

logger = logging.getLogger(__name__)


class CelerySqsInstrumentor(BaseInstrumentor):
    """
    An instrumentor for Celery's (well, Kombu's) SQS transport. It constructs AWSRequest objects manually, meaning
    telemetry via botocore/boto3sqs instrumentations is sidestepped. Here we hook in and grab the message IDs for
    trace spans and correlation.
    """

    def instrumentation_dependencies(self) -> Collection[str]:
        return _instruments

    def _instrument(self, **kwargs):
        tracer_provider = kwargs.get("tracer_provider")

        # pylint: disable=attribute-defined-outside-init
        self._tracer = get_tracer(
            __name__,
            __version__,
            tracer_provider,
            schema_url="https://opentelemetry.io/schemas/1.11.0",
        )

        self._instrument_delete_message()
        self._instrument_receive_message()
        self._instrument_send_message()

    def _instrument_delete_message(self):
        def delete_message(wrapped, instance, args, kwargs):
            with self._tracer.start_as_current_span("DeleteMessage", kind=SpanKind.CLIENT) as span:
                span.set_attribute("eas.receipt_handle", args[1])
                return wrapped(*args, **kwargs)

        wrap_function_wrapper(
            kombu.asynchronous.aws.sqs.connection.AsyncSQSConnection, "delete_message_from_handle", delete_message
        )

    def _instrument_receive_message(self):
        def receive_message(wrapped, instance, args, kwargs):
            with self._tracer.start_as_current_span("ReceiveMessage", kind=SpanKind.CONSUMER) as span:
                span.set_attribute("eas.queue", args[0])

                callback = kwargs["callback"]

                def wrapped_callback(*args, **kwargs):
                    aws_response = args[0]
                    for message in aws_response["Messages"]:
                        with self._tracer.start_as_current_span("ReceiveMessage " + message["MessageId"]) as span:
                            span.set_attribute("messaging.message.id", message["MessageId"])
                            span.add_event(message["MessageId"])
                            logger.info("Sent message %s", message["MessageId"])

                    callback(*args, **kwargs)

                kwargs["callback"] = wrapped_callback
                return wrapped(*args, **kwargs)

        wrap_function_wrapper(
            kombu.asynchronous.aws.sqs.connection.AsyncSQSConnection, "receive_message", receive_message
        )

    def _instrument_send_message(self):
        def send_message(wrapped, instance, args, kwargs):
            with self._tracer.start_as_current_span("SendMessage", kind=SpanKind.PRODUCER) as span:
                span.set_attribute("eas.queue", args[0])

                callback = kwargs["callback"]

                def wrapped_callback(*args, **kwargs):
                    aws_response = args[0]
                    span.set_attribute("messaging.message.id", aws_response["MessageId"])
                    logger.info("Sent message %s", aws_response["MessageId"])

                    callback(*args, **kwargs)

                kwargs["callback"] = wrapped_callback
                return wrapped(*args, **kwargs)

        wrap_function_wrapper(kombu.asynchronous.aws.sqs.connection.AsyncSQSConnection, "send_message", send_message)

    def _uninstrument(self, **kwargs):
        return super()._uninstrument(**kwargs)
