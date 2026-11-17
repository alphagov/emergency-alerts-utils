import logging
import sys

from flask import Flask, Response, current_app, request
from flask.logging import default_handler
from pythonjsonlogger.core import RESERVED_ATTRS
from pythonjsonlogger.json import JsonFormatter


def init_app(app: Flask):
    app.config.setdefault("NOTIFY_LOG_LEVEL", "DEBUG")
    app.config.setdefault("EAS_APP_NAME", "none")

    override_root_logger(app)

    # Flask sets up its own handler prior, but we want to inherit Python's root's
    app.logger.removeHandler(default_handler)

    app.after_request(_log_after_request)
    app.logger.info("Logging configured")


def override_root_logger(app: Flask):
    root = logging.getLogger()

    handler = _create_console_handler()

    root.addHandler(handler)
    root.setLevel(logging.DEBUG)

    # Very noisy in debug:
    logging.getLogger("botocore").setLevel(logging.INFO)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)
    logging.getLogger("opentelemetry.instrumentation.botocore").setLevel(logging.INFO)
    logging.getLogger("boto3.resources").setLevel(logging.INFO)
    logging.getLogger("amazon.opentelemetry.distro._aws_metric_attribute_generator").setLevel(logging.INFO)

    logging.info("Root logger configured")

    app.logger.setLevel(logging.getLevelName(app.config["NOTIFY_LOG_LEVEL"]))


def _create_console_handler():
    handler = logging.StreamHandler(sys.stdout)

    # Allow the handler to log anything - we filter by setting logger levels
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(
        JsonFormatterForCloudWatch(
            # Let these attributes be logged too:
            reserved_attrs=list(set(RESERVED_ATTRS) - {"process", "name", "levelname", "thread"})
        )
    )

    handler.addFilter(CodeContextFilter())
    handler.addFilter(OtelFilter())

    return handler


def _log_after_request(response: Response):
    current_app.logger.info(
        "Responded %s: %s %s %s", response.status, request.remote_addr, request.method, request.full_path
    )
    return response


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


class OtelFilter(logging.Filter):
    def filter(self, record):
        # This is pointless as span ID and trace ID end up as 0 anyway
        if hasattr(record, "otelTraceSampled"):
            del record.otelTraceSampled

        return record
