import time
from contextlib import contextmanager

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


def make_task(app):
    class NotifyTask(Task):
        abstract = True
        start = None

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
                        "queue_name": self.queue_name,
                        "return_value": retval,
                        "task_id": task_id,
                        "args": args,
                        "kwargs": kwargs,
                    }
                )

        def on_failure(self, exc, task_id, args, kwargs, einfo):
            # enables request id tracing for these logs
            with self.app_context():
                current_app.logger.error(
                    f"Celery task {self.name} failed",
                    extra={
                        "python_module": __name__,
                        "queue_name": self.queue_name,
                        "exception": str(exc),
                        "exception_info": einfo,
                        "task_id": task_id,
                        "args": args,
                        "kwargs": kwargs,
                    }
                )

        def __call__(self, *args, **kwargs):
            # ensure task has flask context to access config, logger, etc
            with self.app_context():
                self.start = time.monotonic()
                # return super().__call__(*args, **kwargs)
                return self.run(*args, **kwargs)

    return NotifyTask


class NotifyCelery(Celery):
    def init_app(self, app):
        super().__init__(
            task_cls=make_task(app),
        )

        # Configure Celery app with options from the main app config.
        self.conf.update(app.config["CELERY"])
        self.set_default()
        app.extensions["celery"] = self

    def send_task(self, name, args=None, kwargs=None, **other_kwargs):
        other_kwargs["headers"] = other_kwargs.get("headers") or {}

        if has_request_context() and hasattr(request, "request_id"):
            other_kwargs["headers"]["notify_request_id"] = request.request_id

        elif has_app_context() and "request_id" in g:
            other_kwargs["headers"]["notify_request_id"] = g.request_id

        return super().send_task(name, args, kwargs, **other_kwargs)
