import logging as builtin_logging

from emergency_alerts_utils import logging


def test_logging_module_sets_up_root_logger():
    # Correctly instantiated loggers will have at least one handler
    assert builtin_logging.getLogger().hasHandlers()


def test_root_handler_is_correctly_configured():
    class App:
        config = {
            "EAS_APP_NAME": "bar",
            "NOTIFY_LOG_LEVEL": "ERROR",
        }

    app = App()

    handler = logging._create_console_handler(app)
    assert handler is not None
    assert type(handler) is builtin_logging.StreamHandler
    assert type(handler.formatter) is logging.JsonFormatterForCloudWatch


def test_root_handler_has_appropriate_filters():
    class App:
        config = {
            "EAS_APP_NAME": "bar",
            "NOTIFY_LOG_LEVEL": "ERROR",
        }

    app = App()

    handler = logging._create_console_handler(app)
    filters = list(map(lambda filter: type(filter), handler.filters))
    assert logging.CodeContextFilter in filters
    assert logging.OtelFilter in filters
