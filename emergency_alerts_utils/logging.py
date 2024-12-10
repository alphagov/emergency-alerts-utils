import logging
import logging.handlers
import sys

from flask import g, request
from flask.ctx import has_app_context, has_request_context
from pythonjsonlogger.jsonlogger import JsonFormatter


def init_app(app, statsd_client=None):
    app.config.setdefault("NOTIFY_LOG_LEVEL", "INFO")
    app.config.setdefault("EAS_APP_NAME", "none")

    configure_application_logger(app)

    app.logger.info("Logging configured")


def configure_application_logger(app):
    del app.logger.handlers[:]

    handler = _configure_root_handler(app)

    app.logger.addHandler(handler)
    app.logger.setLevel(logging.getLevelName(app.config["NOTIFY_LOG_LEVEL"]))


def _configure_root_handler(app):
    handler = logging.StreamHandler(sys.stdout)

    handler.setLevel(logging.getLevelName(app.config["NOTIFY_LOG_LEVEL"]))
    handler.setFormatter(JsonFormatterForCloudWatch())

    handler.addFilter(AppNameFilter(app.config["EAS_APP_NAME"]))
    handler.addFilter(RequestIdFilter())
    handler.addFilter(ServiceIdFilter())

    return handler


class JsonFormatterForCloudWatch(JsonFormatter):
    def formatException(self, exc_info):
        """
        Replace '\n' with '\r' to prevent CloudWatch adding
        each newline as a separate log entry
        """
        result = super().formatException(exc_info)
        return result.replace("\n", "\r")


class AppNameFilter(logging.Filter):
    def __init__(self, app_name):
        self.app_name = app_name

    def filter(self, record):
        record.app_name = self.app_name

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
