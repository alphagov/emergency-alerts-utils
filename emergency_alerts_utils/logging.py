import logging
import sys

from flask import g, request
from flask.ctx import has_app_context, has_request_context
from pythonjsonlogger.core import RESERVED_ATTRS
from pythonjsonlogger.json import JsonFormatter


def init_app(app):
    app.config.setdefault("NOTIFY_LOG_LEVEL", "INFO")
    app.config.setdefault("EAS_APP_NAME", "none")

    override_root_logger(app)

    app.logger.info("Logging configured")


def override_root_logger(app):
    root = logging.getLogger()

    handler = _create_console_handler(app)

    root.addHandler(handler)
    root.setLevel(logging.INFO)

    logging.getLogger("celery").setLevel(logging.DEBUG)
    logging.getLogger("kombu").setLevel(logging.DEBUG)
    logging.getLogger("billiard").setLevel(logging.DEBUG)
    logging.getLogger("botocore.endpoint").setLevel(logging.DEBUG)
    logging.getLogger("botocore.hooks").setLevel(logging.DEBUG)
    logging.getLogger("botocore.parsers").setLevel(logging.DEBUG)

    logging.info("Root logger configured")

    app.logger.setLevel(logging.getLevelName(app.config["NOTIFY_LOG_LEVEL"]))


def _create_console_handler(app):
    handler = logging.StreamHandler(sys.stdout)

    # Allow the handler to log anything - we filter by setting logger levels
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(
        JsonFormatterForCloudWatch(reserved_attrs=list(set(RESERVED_ATTRS) - {"process", "thread", "name"}))
    )

    handler.addFilter(CodeContextFilter())

    return handler


class JsonFormatterForCloudWatch(JsonFormatter):
    def formatException(self, exc_info):
        """
        Replace '\n' with '\r' to prevent CloudWatch adding
        each newline as a separate log entry
        """
        result = super().formatException(exc_info)
        return result.replace("\n", "\r")


class CodeContextFilter(logging.Filter):
    def filter(self, record):
        record.line = f"{record.filename}:{record.lineno}"

        return record


class RequestIdFilter(logging.Filter):
    @property
    def request_id(self):
        if has_request_context() and hasattr(request, "request_id"):
            return request.request_id
        elif has_app_context() and "request_id" in g:
            return g.request_id
        else:
            return "no-request-id"

    def filter(self, record):
        record.request_id = self.request_id

        return record


class ServiceIdFilter(logging.Filter):
    @property
    def service_id(self):
        if has_app_context() and "service_id" in g:
            return g.service_id
        else:
            return "no-service-id"

    def filter(self, record):
        record.service_id = self.service_id

        return record
