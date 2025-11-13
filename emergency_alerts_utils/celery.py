from kombu.transport import SQS


class LoggingSQSChannel(SQS.Channel):

    def _message_to_python(self, message, queue_name, q_url):
        logger.info("Converted SQS message: %s", str(message))
        logger.info("Converted stack: %s", "".join(traceback.format_stack()))
        return super()._message_to_python(message, queue_name, q_url)

    def _put(self, queue, message, **kwargs):  # noqa: C901
        """Put message onto queue."""
        q_url = self._new_queue(queue)
        kwargs = {"QueueUrl": q_url}
        if "properties" in message:
            if "message_attributes" in message["properties"]:
                # we don't want to want to have the attribute in the body
                kwargs["MessageAttributes"] = message["properties"].pop("message_attributes")
            if queue.endswith(".fifo"):
                if "MessageGroupId" in message["properties"]:
                    kwargs["MessageGroupId"] = message["properties"]["MessageGroupId"]
                else:
                    kwargs["MessageGroupId"] = "default"
                if "MessageDeduplicationId" in message["properties"]:
                    kwargs["MessageDeduplicationId"] = message["properties"]["MessageDeduplicationId"]
                else:
                    kwargs["MessageDeduplicationId"] = str(uuid.uuid4())
            else:
                if "DelaySeconds" in message["properties"]:
                    kwargs["DelaySeconds"] = message["properties"]["DelaySeconds"]

        if self.sqs_base64_encoding:
            body = SQS.AsyncMessage().encode(dumps(message))
        else:
            body = dumps(message)
        kwargs["MessageBody"] = body

        c = self.sqs(queue=self.canonical_queue_name(queue))
        if message.get("redelivered"):
            logger.info("SQS change message visibility? %s", message)
            c.change_message_visibility(
                QueueUrl=q_url, ReceiptHandle=message["properties"]["delivery_tag"], VisibilityTimeout=0
            )
        else:
            resp = c.send_message(**kwargs)
            logger.info("SQS send: %s", str(resp))

    def basic_ack(self, delivery_tag, multiple=False):
        try:
            message = self.qos.get(delivery_tag).delivery_info
            sqs_message = message["sqs_message"]
        except KeyError:
            logger.exception("basic_ack key error?")
            super().basic_ack(delivery_tag)
        else:
            logger.info(f"basic_ack: {str(delivery_tag)} / {message}")

            queue = None
            if "routing_key" in message:
                queue = self.canonical_queue_name(message["routing_key"])

            try:
                self.sqs(queue=queue).delete_message(
                    QueueUrl=message["sqs_queue"], ReceiptHandle=sqs_message["ReceiptHandle"]
                )
            except ClientError as exception:
                if exception.response["Error"]["Code"] == "AccessDenied":
                    raise SQS.AccessDeniedQueueException(exception.response["Error"]["Message"])
                super().basic_reject(delivery_tag)
            else:
                super().basic_ack(delivery_tag)


SQS.Channel = LoggingSQSChannel

import logging
import time
import traceback
import uuid
from contextlib import contextmanager
from os import getpid

from botocore.exceptions import ClientError
from celery import Celery, Task
from celery.signals import setup_logging, worker_init, worker_process_init
from flask import current_app, g, request
from flask.ctx import has_app_context, has_request_context
from kombu.asynchronous.aws.sqs.message import AsyncMessage
from kombu.utils.json import dumps
from opentelemetry import trace
from opentelemetry.instrumentation.celery import CeleryInstrumentor

tracer = trace.get_tracer("celery")


@setup_logging.connect
def setup_logger(*args, **kwargs):
    logger.info("setup_logger")
    """
    Using '"worker_hijack_root_logger": False' in the Celery config
    should block celery from overriding the logger configuration.
    In practice, this doesn't seem to work, so we intercept this
    celery signal and just do a NOP
    """
    pass


logger = logging.getLogger(__name__)


def make_task(app):  # noqa: C901
    class NotifyTask(Task):
        abstract = True
        start = time.monotonic()

        def __init__(self, *args, **kwargs):
            # custom task-decorator arguments get applied as class attributes (!),
            # provide a default if this is missing
            self.early_log_level = getattr(self, "early_log_level", logging.INFO)
            super().__init__(*args, **kwargs)

        @property
        def queue_name(self):
            delivery_info = self.request.delivery_info or {}
            return delivery_info.get("routing_key", "none")

        @property
        def request_id(self):
            # Note that each header is a direct attribute of the
            # task context (aka "request").
            return self.request.get("notify_request_id")

        @contextmanager
        def app_context(self):
            with app.app_context():
                # Add 'request_id' to 'g' so that it gets logged.
                g.request_id = self.request_id
                yield

        def on_success(self, retval, task_id, args, kwargs):
            # enables request id tracing for these logs
            with self.app_context():
                elapsed_time = time.monotonic() - self.start

                current_app.logger.info(
                    f"Celery task {self.name} took {elapsed_time:.4f}",
                    extra={
                        "python_module": __name__,
                        "celery_task": self.name,
                        "celery_task_id": task_id,
                        "queue_name": self.queue_name,
                        "time_taken": elapsed_time,
                        "celery_pid": getpid(),
                    },
                )

        def on_retry(self, exc, task_id, args, kwargs, einfo):
            # enables request id tracing for these logs
            with self.app_context():
                elapsed_time = time.monotonic() - self.start

                current_app.logger.warning(
                    "Celery task %s (queue: %s) failed for retry after %.4f",
                    self.name,
                    self.queue_name,
                    elapsed_time,
                    extra={
                        "python_module": __name__,
                        "celery_task": self.name,
                        "celery_task_id": task_id,
                        "queue_name": self.queue_name,
                        "time_taken": elapsed_time,
                        "celery_pid": getpid(),
                        "error": exc,
                        "error_info": str(einfo),
                    },
                )

        def on_failure(self, exc, task_id, args, kwargs, einfo):
            # enables request id tracing for these logs
            with self.app_context():
                elapsed_time = time.monotonic() - self.start

                current_app.logger.exception(
                    "Celery task %s (queue: %s) failed after %.4f",
                    self.name,
                    self.queue_name,
                    elapsed_time,
                    extra={
                        "celery_task": self.name,
                        "celery_task_id": task_id,
                        "queue_name": self.queue_name,
                        "time_taken": elapsed_time,
                        "celery_pid": getpid(),
                        "error": exc,
                        "error_info": str(einfo),
                    },
                )

        def before_start(self, task_id, args, kwargs):
            # enables request id tracing for these logs
            with self.app_context():
                current_app.logger.info(
                    "Celery task %s (queue: %s) started",
                    self.name,
                    self.queue_name,
                    extra={
                        "python_module": __name__,
                        "celery_task": self.name,
                        "celery_task_id": task_id,
                        "queue_name": self.queue_name,
                        "celery_pid": getpid(),
                    },
                )

        def __call__(self, *args, **kwargs):
            # ensure task has flask context to access config, logger, etc
            with self.app_context():
                with tracer.start_as_current_span(f"celery task {self.name}"):
                    self.start = time.monotonic()
                    return super().__call__(*args, **kwargs)

    return NotifyTask


@worker_process_init.connect(weak=False)
def init_celery_tracing_process(*args, **kwargs):
    from opentelemetry.instrumentation.auto_instrumentation import initialize

    initialize()
    from opentelemetry.instrumentation.boto3sqs import Boto3SQSInstrumentor

    Boto3SQSInstrumentor().instrument()

    logger.info("init_celery_tracing_process")


@worker_init.connect(weak=False)
def init_celery_tracing(*args, **kwargs):
    from opentelemetry.instrumentation.boto3sqs import Boto3SQSInstrumentor

    Boto3SQSInstrumentor().instrument()
    from opentelemetry.instrumentation.auto_instrumentation import initialize

    initialize()

    logger.info("init_celery_tracing")


class NotifyCelery(Celery):
    def init_app(self, app):
        super().__init__(
            task_cls=make_task(app),
        )
        self.config_from_object(app.config["CELERY"])
        CeleryInstrumentor().instrument()

    def send_task(self, name, args=None, kwargs=None, **other_kwargs):
        logger = logging.getLogger("celery")  # Don't require a Flask context to log sends

        other_kwargs["headers"] = other_kwargs.get("headers") or {}

        if has_request_context() and hasattr(request, "request_id"):
            other_kwargs["headers"]["notify_request_id"] = request.request_id
            logger = current_app.logger

        elif has_app_context() and "request_id" in g:
            other_kwargs["headers"]["notify_request_id"] = g.request_id
            logger = current_app.logger

        logger.info("Sending Celery task %s: %s / %s", name, kwargs, other_kwargs)

        sent = super().send_task(name, args, kwargs, **other_kwargs)

        logger.info("Sent task: %s", sent)
        return sent


class QueueNames:
    PERIODIC = "periodic-tasks"
    BROADCASTS = "broadcast-tasks"
    GOVUK_ALERTS = "govuk-alerts"


class TaskNames:
    PUBLISH_GOVUK_ALERTS = "publish-govuk-alerts"
    SEND_BROADCAST_EVENT = "send-broadcast-event"
    SEND_BROADCAST_PROVIDER_MESSAGE = "send-broadcast-provider-message"
    TRIGGER_LINK_TEST = "trigger-link-test"

    # Scheduled
    TRIGGER_GOVUK_HEALTHCHECK = "trigger-govuk-alerts-healthcheck"
    RUN_HEALTH_CHECK = "run-health-check"
    DELETE_VERIFY_CODES = "delete-verify-codes"
    DELETE_INVITATIONS = "delete-invitations"
    TRIGGER_LINK_TESTS = "trigger-link-tests"
    AUTO_EXPIRE_BROADCAST_MESSAGES = "auto-expire-broadcast-messages"
    REMOVE_YESTERDAYS_PLANNED_TESTS_ON_GOVUK_ALERTS = "remove-yesterdays-planned-tests-on-govuk-alerts"
    DELETE_OLD_RECORDS_FROM_EVENTS_TABLE = "delete-old-records-from-events-table"
    VALIDATE_FUNCTIONAL_TEST_ACCOUNT_EMAILS = "validate-functional-test-account-emails"
    QUEUE_AFTER_ALERT_ACTIVITIES = "queue-after-alert-activities"
