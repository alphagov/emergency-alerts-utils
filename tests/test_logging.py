import logging as builtin_logging

from flask import Flask

from emergency_alerts_utils import logging


def test_init_removes_app_default_handler(mocker):
    app = Flask("test")
    spy_remove_handler = mocker.spy(app.logger, "removeHandler")

    logging.init_app(app)

    spy_remove_handler.assert_called_once()
    assert len(app.logger.handlers) == 0  # Use parent handler(s)


def test_flask_app_registers_log_after_request():
    app = Flask("test")

    logging.init_app(app)
    assert list(app.after_request_funcs.values()) == [[logging._log_after_request]]


def test_logging_module_sets_up_root_logger():
    # Correctly instantiated loggers will have at least one handler
    assert builtin_logging.getLogger().hasHandlers()


def test_root_handler_is_correctly_configured():
    handler = logging._create_console_handler()
    assert handler is not None
    assert type(handler) is builtin_logging.StreamHandler
    assert type(handler.formatter) is logging.JsonFormatterForCloudWatch


def test_root_handler_has_appropriate_filters():
    handler = logging._create_console_handler()
    filters = list(map(lambda filter: type(filter), handler.filters))
    assert logging.CodeContextFilter in filters
    assert logging.OtelFilter in filters
