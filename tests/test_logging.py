import json
import logging as builtin_logging

import pythonjsonlogger.jsonlogger

from emergency_alerts_utils import logging


def test_logging_module_sets_up_root_and_celery_loggers():
    # Correctly instantiated loggers will have at least one handler
    assert builtin_logging.getLogger().hasHandlers()
    assert builtin_logging.getLogger("celery").hasHandlers()


def test_handlers_are_correctly_configured():
    class App:
        config = {
            "NOTIFY_APP_NAME": "bar",
            "NOTIFY_LOG_LEVEL": "ERROR",
        }

    app = App()

    handler1 = logging._configure_root_handler(app)
    assert handler1 is not None
    assert type(handler1) == builtin_logging.StreamHandler
    assert type(handler1.formatter) == pythonjsonlogger.jsonlogger.JsonFormatter

    handler2 = logging._configure_notraceback_handler(app)
    assert handler2 is not None
    assert type(handler2) == builtin_logging.StreamHandler
    assert type(handler2.formatter) == logging.NoExceptionFormatter


def test_configure_root_handler_adds_appropriate_filters():
    class App:
        config = {
            "NOTIFY_APP_NAME": "bar",
            "NOTIFY_LOG_LEVEL": "ERROR",
        }

    app = App()

    handler = logging._configure_root_handler(app)
    filters = list(map(lambda filter: type(filter), handler.filters))
    assert logging.AppNameFilter in filters
    assert logging.RequestIdFilter in filters
    assert logging.ServiceIdFilter in filters


def test_configure_notraceback_handler_adds_appropriate_filters():
    class App:
        config = {
            "NOTIFY_APP_NAME": "bar",
            "NOTIFY_LOG_LEVEL": "ERROR",
        }

    app = App()

    handler = logging._configure_notraceback_handler(app)
    filters = list(map(lambda filter: type(filter), handler.filters))
    assert logging.SuppressTracebackFilter in filters


def test_base_json_formatter_contains_service_id(tmpdir):
    record = builtin_logging.LogRecord(
        name="log thing", level="info", pathname="path", lineno=123, msg="message to log", exc_info=None, args=None
    )

    service_id_filter = logging.ServiceIdFilter()
    assert json.loads(logging.JsonFormatter().format(record))["message"] == "message to log"
    assert service_id_filter.filter(record).service_id == "no-service-id"
