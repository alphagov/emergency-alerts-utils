import logging
import time
from contextlib import contextmanager
from os import getpid

from celery import Celery, Task
from celery.signals import setup_logging
from flask import current_app, g, request
from flask.ctx import has_app_context, has_request_context


@setup_logging.connect
def setup_logger(*args, **kwargs):
    """
    Using '"worker_hijack_root_logger": False' in the Celery config
    should block celery from overriding the logger configuration.
    In practice, this doesn't seem to work, so we intercept this
    celery signal and just do a NOP
    """
    pass


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
                self.start = time.monotonic()
                return super().__call__(*args, **kwargs)

    return NotifyTask


class NotifyCelery(Celery):
    def init_app(self, app):
        super().__init__(
            task_cls=make_task(app),
        )
        self.config_from_object(app.config["CELERY"])

    def send_task(self, name, args=None, kwargs=None, **other_kwargs):
        other_kwargs["headers"] = other_kwargs.get("headers") or {}

        if has_request_context() and hasattr(request, "request_id"):
            other_kwargs["headers"]["notify_request_id"] = request.request_id

        elif has_app_context() and "request_id" in g:
            other_kwargs["headers"]["notify_request_id"] = g.request_id

        return super().send_task(name, args, kwargs, **other_kwargs)


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
