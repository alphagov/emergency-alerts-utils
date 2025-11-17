import logging
import sys

from pythonjsonlogger.core import RESERVED_ATTRS
from pythonjsonlogger.json import JsonFormatter


def init_app(app):
    app.config.setdefault("NOTIFY_LOG_LEVEL", "DEBUG")
    app.config.setdefault("EAS_APP_NAME", "none")

    override_root_logger(app)

    app.logger.info("Logging configured")


def override_root_logger(app):
    root = logging.getLogger()

    handler = _create_console_handler(app)

    root.addHandler(handler)
    root.setLevel(logging.DEBUG)

    # logging.getLogger("celery").setLevel(logging.DEBUG)
    # logging.getLogger("kombu").setLevel(logging.DEBUG)
    # logging.getLogger("billiard").setLevel(logging.DEBUG)
    logging.getLogger("botocore").setLevel(logging.INFO)
    # logging.getLogger("botocore.hooks").setLevel(logging.DEBUG)
    # logging.getLogger("botocore.parsers").setLevel(logging.DEBUG)

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
