import json
import logging as builtin_logging
import logging.handlers as builtin_logging_handlers

import pytest
import pythonjsonlogger.jsonlogger

from emergency_alerts_utils import logging


def test_get_handlers_sets_up_logging_appropriately_with_debug(tmpdir):
    class App:
        config = {
            "EMERGENCY_ALERTS_LOG_PATH": str(tmpdir / "foo"),
            "EMERGENCY_ALERTS_APP_NAME": "bar",
            "EMERGENCY_ALERTS_LOG_LEVEL": "ERROR",
        }
        debug = True

    app = App()

    handlers = logging.get_handlers(app)

    assert len(handlers) == 1
    assert type(handlers[0]) == builtin_logging.StreamHandler
    assert type(handlers[0].formatter) == logging.CustomLogFormatter
    assert not (tmpdir / "foo").exists()


@pytest.mark.parametrize(
    "platform",
    [
        "local",
        "paas",
        "something-else",
    ],
)
def test_get_handlers_sets_up_logging_appropriately_without_debug_when_not_on_ecs(tmpdir, platform):
    class App:
        config = {
            # make a tempfile called foo
            "EMERGENCY_ALERTS_LOG_PATH": str(tmpdir / "foo"),
            "EMERGENCY_ALERTS_APP_NAME": "bar",
            "EMERGENCY_ALERTS_LOG_LEVEL": "ERROR",
            "EMERGENCY_ALERTS_RUNTIME_PLATFORM": platform,
        }
        debug = False

    app = App()

    handlers = logging.get_handlers(app)

    assert len(handlers) == 2
    assert type(handlers[0]) == builtin_logging.StreamHandler
    assert type(handlers[0].formatter) == pythonjsonlogger.jsonlogger.JsonFormatter

    assert type(handlers[1]) == builtin_logging_handlers.WatchedFileHandler
    assert type(handlers[1].formatter) == pythonjsonlogger.jsonlogger.JsonFormatter

    dir_contents = tmpdir.listdir()
    assert len(dir_contents) == 1
    assert dir_contents[0].basename == "foo.json"


def test_get_handlers_sets_up_logging_appropriately_without_debug_on_ecs(tmpdir):
    class App:
        config = {
            # make a tempfile called foo
            "EMERGENCY_ALERTS_LOG_PATH": str(tmpdir / "foo"),
            "EMERGENCY_ALERTS_APP_NAME": "bar",
            "EMERGENCY_ALERTS_LOG_LEVEL": "ERROR",
            "EMERGENCY_ALERTS_RUNTIME_PLATFORM": "ecs",
        }
        debug = False

    app = App()

    handlers = logging.get_handlers(app)

    assert len(handlers) == 1
    assert type(handlers[0]) == builtin_logging.StreamHandler
    assert type(handlers[0].formatter) == pythonjsonlogger.jsonlogger.JsonFormatter

    assert not (tmpdir / "foo.json").exists()


def test_base_json_formatter_contains_service_id(tmpdir):
    record = builtin_logging.LogRecord(
        name="log thing", level="info", pathname="path", lineno=123, msg="message to log", exc_info=None, args=None
    )

    service_id_filter = logging.ServiceIdFilter()
    assert json.loads(logging.JsonFormatter().format(record))["message"] == "message to log"
    assert service_id_filter.filter(record).service_id == "no-service-id"
