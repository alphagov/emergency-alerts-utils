import json
import logging as builtin_logging

from emergency_alerts_utils import logging


def test_logging_module_sets_up_root_logger():
    # Correctly instantiated loggers will have at least one handler
    assert builtin_logging.getLogger().hasHandlers()


def test_root_handler_is_correctly_configured():
    class App:
        config = {
            "NOTIFY_APP_NAME": "bar",
            "NOTIFY_LOG_LEVEL": "ERROR",
        }

    app = App()

    handler = logging._configure_root_handler(app)
    assert handler is not None
    assert type(handler) is builtin_logging.StreamHandler
    assert type(handler.formatter) is logging.JsonFormatterForCloudWatch


def test_root_handler_has_appropriate_filters():
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


def test_filter_adds_service_id_to_log_record():
    record = builtin_logging.LogRecord(
        name="log thing", level="info", pathname="path", lineno=123, msg="message to log", exc_info=None, args=None
    )

    service_id_filter = logging.ServiceIdFilter()
    assert json.loads(logging.JsonFormatterForCloudWatch().format(record))["message"] == "message to log"
    assert service_id_filter.filter(record).service_id == "no-service-id"


def test_filter_adds_request_id_to_log_record():
    record = builtin_logging.LogRecord(
        name="log thing", level="info", pathname="path", lineno=123, msg="message to log", exc_info=None, args=None
    )

    service_id_filter = logging.RequestIdFilter()
    assert json.loads(logging.JsonFormatterForCloudWatch().format(record))["message"] == "message to log"
    assert service_id_filter.filter(record).request_id == "no-request-id"


def test_filter_adds_app_name_to_log_record():
    record = builtin_logging.LogRecord(
        name="log thing", level="info", pathname="path", lineno=123, msg="message to log", exc_info=None, args=None
    )

    service_id_filter = logging.AppNameFilter(app_name="test_name")
    assert json.loads(logging.JsonFormatterForCloudWatch().format(record))["message"] == "message to log"
    assert service_id_filter.filter(record).app_name == "test_name"
