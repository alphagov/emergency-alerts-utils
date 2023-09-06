import logging
import logging.handlers
import re
import sys
from itertools import product

from flask import g, request
from flask.ctx import has_app_context, has_request_context
from pythonjsonlogger.jsonlogger import JsonFormatter

# from pathlib import Path


LOG_FORMAT = (
    "%(asctime)s %(app_name)s %(name)s %(levelname)s " '%(request_id)s "%(message)s" [in %(pathname)s:%(lineno)d]'
)
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

logger = logging.getLogger(__name__)


def init_app(app, statsd_client=None):
    app.config.setdefault("NOTIFY_LOG_LEVEL", "INFO")
    app.config.setdefault("NOTIFY_APP_NAME", "none")
    app.config.setdefault("NOTIFY_LOG_PATH", "./log/application.log")
    app.config.setdefault("NOTIFY_RUNTIME_PLATFORM", None)

    logging.getLogger().addHandler(logging.NullHandler())

    del app.logger.handlers[:]

    # if app.config["NOTIFY_RUNTIME_PLATFORM"] != "ecs":
    #     # TODO: ecs-migration: check if we still need this function after we migrate to ecs
    #     ensure_log_path_exists(app.config["NOTIFY_LOG_PATH"])

    handlers = get_handlers(app)
    loglevel = logging.getLevelName(app.config["NOTIFY_LOG_LEVEL"])
    loggers = [app.logger, logging.getLogger("utils")]
    for logger_instance, handler in product(loggers, handlers):
        logger_instance.addHandler(handler)
        logger_instance.setLevel(loglevel)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("s3transfer").setLevel(logging.WARNING)

    # _configure_celery_logger()

    app.logger.info("Logging configured")


# def ensure_log_path_exists(path):
#     """
#     This function assumes you're passing a path to a file and attempts to create
#     the path leading to that file.
#     """
#     try:
#         Path(path).parent.mkdir(mode=755, parents=True)
#     except FileExistsError:
#         pass


def get_handlers(app):
    handlers = []
    # standard_formatter = CustomLogFormatter(LOG_FORMAT, TIME_FORMAT)
    # json_formatter = JsonFormatter(LOG_FORMAT, TIME_FORMAT)
    json_formatter = JsonFormatter()

    stream_handler = logging.StreamHandler(sys.stdout)

    # if app.debug:
    #     # turn off 200 OK static logs in development
    #     def is_200_static_log(log):
    #         msg = log.getMessage()
    #         return not ("GET /static/" in msg and " 200 " in msg)

    #     logging.getLogger("werkzeug").addFilter(is_200_static_log)

    #     # human readable stdout logs
    #     handlers.append(configure_handler(stream_handler, app, standard_formatter))
    #     return handlers

    # stream json to stdout in all cases
    handlers.append(configure_handler(stream_handler, app, json_formatter))

    # TODO: ecs-migration: delete this when we migrate to ecs
    # only write json to file if we're not running on ECS
    # if app.config["NOTIFY_RUNTIME_PLATFORM"] != "ecs":
    #     # machine readable json to both file and stdout
    #     file_handler = logging.handlers.WatchedFileHandler(filename=f"{app.config['NOTIFY_LOG_PATH']}.json")
    #     handlers.append(configure_handler(file_handler, app, json_formatter))

    return handlers


def configure_handler(handler, app, formatter):
    handler.setLevel(logging.getLevelName(app.config["NOTIFY_LOG_LEVEL"]))
    handler.setFormatter(formatter)
    handler.addFilter(AppNameFilter(app.config["NOTIFY_APP_NAME"]))
    handler.addFilter(RequestIdFilter())
    handler.addFilter(ServiceIdFilter())
    handler.addFilter(SuppressTracebackFilter())

    return handler


def _configure_celery_logger():
    """
    Use a custom handler for error logging in Celery to suppress output
    of traceback information that clutters the Cloudwatch logs by
    producing a log entry for each line in the stack trace.
    """
    # celeryLogger = logging.getLogger("celery")
    # celeryLogger.addHandler(logging.NullHandler())
    # celeryLogger.setLevel(logging.ERROR)
    # celery_handler = NoTracebackHandler()
    # celery_handler.setLevel(logging.ERROR)
    # celery_handler.setFormatter(JsonFormatter())
    # celeryLogger.addHandler(celery_handler)

    celeryLogger = logging.getLogger("celery")
    celeryLogger.addHandler(logging.NullHandler())
    celeryLogger.setLevel(logging.ERROR)
    celery_handler = logging.StreamHandler(sys.stdout)
    celery_handler.setLevel(logging.ERROR)
    celery_handler.addFilter(SuppressTracebackFilter())
    # celery_handler.setFormatter(JsonFormatter())
    celeryLogger.addHandler(celery_handler)


class NoTracebackHandler(logging.Handler):
    def handle(self, record):
        info, text = record.exc_info, record.exc_text
        record.exc_info, record.exc_text = None, None
        try:
            super().handle(record)
        finally:
            record.exc_info = info
            record.exc_text = text


class SuppressTracebackFilter(logging.Filter):
    def filter(self, record):
        record.exc_info = None
        record.exc_text = None
        return True


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


class CustomLogFormatter(logging.Formatter):
    """Accepts a format string for the message and formats it with the extra fields"""

    FORMAT_STRING_FIELDS_PATTERN = re.compile(r"\((.+?)\)", re.IGNORECASE)

    def add_fields(self, record):
        for field in self.FORMAT_STRING_FIELDS_PATTERN.findall(self._fmt):
            record.__dict__[field] = record.__dict__.get(field)
        return record

    def format(self, record):
        record = self.add_fields(record)
        try:
            record.msg = str(record.msg).format(**record.__dict__)
        except (KeyError, IndexError) as e:
            logger.exception(f"failed to format log message: {e} not found")
        return super(CustomLogFormatter, self).format(record)


# class JsonFormatterNoNewlines(JsonFormatter):
# def format(self, record):
#     record.exc_info = record.exc_info.splitlines("\n"), "\r")
#     return super().format(record)

# def formatException(self, exc_info):
#     return exc_info.replace("\n", "\r")


class JSONFormatter(JsonFormatter):
    def process_log_record(self, log_record):
        rename_map = {
            "asctime": "time",
            "request_id": "requestId",
            "app_name": "application",
            "service_id": "service_id",
        }
        for key, newkey in rename_map.items():
            log_record[newkey] = log_record.pop(key)
        log_record["logType"] = "application"
        try:
            log_record["message"] = log_record["message"].format(**log_record)
        except (KeyError, IndexError) as e:
            logger.exception(f"failed to format log message: {e} not found")
        return log_record
