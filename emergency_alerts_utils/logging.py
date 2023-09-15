import logging
import logging.handlers
import sys

from flask import g, request
from flask.ctx import has_app_context, has_request_context
from pythonjsonlogger.jsonlogger import JsonFormatter


def init_app(app, statsd_client=None):
    app.config.setdefault("NOTIFY_LOG_LEVEL", "INFO")
    app.config.setdefault("NOTIFY_APP_NAME", "none")

    configure_application_logger(app)

    # app.logger.addHandler(_configure_root_handler(app))
    # app.logger.setLevel(logging.getLevelName(app.config["NOTIFY_LOG_LEVEL"]))

    app.logger.info("Logging configured")


def configure_application_logger(app):
    del app.logger.handlers[:]

    handler = logging.StreamHandler(sys.stdout)

    handler.setLevel(logging.getLevelName(app.config["NOTIFY_LOG_LEVEL"]))
    handler.setFormatter(JsonFormatterForCloudWatch())

    handler.addFilter(AppNameFilter(app.config["NOTIFY_APP_NAME"]))
    handler.addFilter(RequestIdFilter())
    handler.addFilter(ServiceIdFilter())

    app.logger.addHandler(handler)
    app.logger.setLevel(logging.getLevelName(app.config["NOTIFY_LOG_LEVEL"]))


# def configure_celery_logger(app):
#     handler = logging.StreamHandler(sys.stdout)
#     handler.setLevel(logging.getLevelName(app.config["NOTIFY_LOG_LEVEL"]))
#     handler.setFormatter(JsonFormatter())
#     handler.addFilter(SuppressTracebackFilter())
#     app.logger.addHandler(handler)
#     app.logger.setLevel(logging.getLevelName(app.config["NOTIFY_LOG_LEVEL"]))


# def _configure_root_handler(app):
#     handler = logging.StreamHandler(sys.stdout)
#     handler.setLevel(logging.getLevelName(app.config["NOTIFY_LOG_LEVEL"]))
#     handler.setFormatter(JsonFormatter())
#     handler.addFilter(AppNameFilter(app.config["NOTIFY_APP_NAME"]))
#     handler.addFilter(RequestIdFilter())
#     handler.addFilter(ServiceIdFilter())
#     handler.addFilter(SuppressTracebackFilter())
#     return handler


# def configure_notraceback_logger(level, logger):
#     logger.addHandler(_configure_notraceback_handler(level))
#     logger.setLevel(logging.getLevelName(level))
#     logger.propagate = False


# def _configure_notraceback_handler(level):
#     handler = logging.StreamHandler(sys.stdout)
#     handler.setLevel(logging.getLevelName(level))
#     handler.setFormatter(NoExceptionFormatter())
#     handler.addFilter(SuppressTracebackFilter())
#     return handler


# def configure_json_logger(level, logger):
#     logger.addHandler(_configure_json_handler(level))
#     logger.setLevel(logging.getLevelName(level))
#     logger.propagate = False


# def _configure_json_handler(level):
#     handler = logging.StreamHandler(sys.stdout)
#     handler.setLevel(logging.getLevelName(level))
#     handler.setFormatter(JsonFormatter)
#     return handler


class JsonFormatterForCloudWatch(JsonFormatter):
    def formatException(self, exc_info):
        """
        Format an exception so that it prints on a single line.
        """
        result = super().formatException(exc_info)
        return result.replace("\n", "")  # or format into one line however you want to

    # def format(self, record):
    #     s = super().format(record)
    #     if record.exc_text:
    #         s = s.replace('\n', '') + '|'
    #     return s


class SuppressTracebackFilter(logging.Filter):
    def filter(self, record):
        record.exc_info = False
        record.exc_text = None
        return True


class NoExceptionFormatter(logging.Formatter):
    def format(self, record):
        record.exc_text = ""  # ensure formatException is called
        return super(NoExceptionFormatter, self).format(record)

    def formatException(self, record):
        return ""


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
