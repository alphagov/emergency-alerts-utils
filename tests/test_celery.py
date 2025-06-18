import uuid
from unittest.mock import ANY

import pytest
from flask import g
from freezegun import freeze_time

from emergency_alerts_utils.celery import NotifyCelery


@pytest.fixture
def notify_celery(celery_app):
    celery = NotifyCelery()
    celery.init_app(celery_app)
    return celery


@pytest.fixture
def celery_task(notify_celery):
    @notify_celery.task(name=uuid.UUID("f14444da-0676-4dc2-afe7-aca55f18463b"), base=notify_celery.task_cls)
    def test_task(delivery_info=None):
        pass

    return test_task


@pytest.fixture
def async_task(celery_task):
    celery_task.push_request(delivery_info={"routing_key": "test-queue"})
    yield celery_task
    celery_task.pop_request()


@pytest.fixture
def request_id_task(celery_task):
    # Note that each header is a direct attribute of the
    # task context (aka "request").
    celery_task.push_request(notify_request_id="1234")
    yield celery_task
    celery_task.pop_request()


def test_success_should_log_info(mocker, celery_app, async_task):
    logger_mock = mocker.patch.object(celery_app.logger, "info")

    with freeze_time() as frozen:
        async_task()
        frozen.tick(5)

        async_task.on_success(retval=None, task_id=1234, args=[], kwargs={})

    logger_mock.assert_called_once_with(
        "Celery task f14444da-0676-4dc2-afe7-aca55f18463b took 5.0000",
        extra={
            "python_module": "emergency_alerts_utils.celery",
            "celery_task": uuid.UUID("f14444da-0676-4dc2-afe7-aca55f18463b"),
            "celery_task_id": None,
            "queue_name": "test-queue",
            "time_taken": 5.0,
            "process_id": ANY,
        },
    )


def test_success_queue_when_applied_synchronously(mocker, celery_app, celery_task):
    logger_mock = mocker.patch.object(celery_app.logger, "info")

    with freeze_time() as frozen:
        celery_task()
        frozen.tick(5)

        celery_task.on_success(retval=None, task_id=1234, args=[], kwargs={})

    logger_mock.assert_called_once_with(
        "Celery task f14444da-0676-4dc2-afe7-aca55f18463b took 5.0000",
        extra={
            "python_module": "emergency_alerts_utils.celery",
            "celery_task": uuid.UUID("f14444da-0676-4dc2-afe7-aca55f18463b"),
            "celery_task_id": None,
            "queue_name": "none",
            "time_taken": 5.0,
            "process_id": ANY,
        },
    )


def test_failure_should_log_error(mocker, celery_app, async_task):
    logger_mock = mocker.patch.object(celery_app.logger, "error")

    async_task.on_failure(exc=Exception, task_id=1234, args=[], kwargs={}, einfo=None)

    logger_mock.assert_called_once_with(
        "Celery task %s (queue: %s) failed after %.4f",
        uuid.UUID("f14444da-0676-4dc2-afe7-aca55f18463b"),
        "test-queue",
        ANY,
        exc_info=True,
        extra={
            "celery_task": uuid.UUID("f14444da-0676-4dc2-afe7-aca55f18463b"),
            "celery_task_id": None,
            "queue_name": "test-queue",
            "time_taken": ANY,
            "process_id": ANY,
        },
    )


def test_failure_queue_when_applied_synchronously(mocker, celery_app, celery_task):
    logger_mock = mocker.patch.object(celery_app.logger, "error")

    celery_task.on_failure(exc=Exception, task_id=1234, args=[], kwargs={}, einfo=None)

    logger_mock.assert_called_once_with(
        "Celery task %s (queue: %s) failed after %.4f",
        uuid.UUID("f14444da-0676-4dc2-afe7-aca55f18463b"),
        "none",
        ANY,
        exc_info=True,
        extra={
            "celery_task": uuid.UUID("f14444da-0676-4dc2-afe7-aca55f18463b"),
            "celery_task_id": None,
            "queue_name": "none",
            "time_taken": ANY,
            "process_id": ANY,
        },
    )


def test_call_exports_request_id_from_headers(mocker, request_id_task):
    g = mocker.patch("emergency_alerts_utils.celery.g")
    request_id_task()
    assert g.request_id == "1234"


def test_call_copes_if_request_id_not_in_headers(mocker, celery_task):
    g = mocker.patch("emergency_alerts_utils.celery.g")
    celery_task()
    assert g.request_id is None


def test_send_task_injects_global_request_id_into_headers(
    mocker,
    notify_celery,
):
    super_apply = mocker.patch("celery.Celery.send_task")
    g.request_id = "1234"
    notify_celery.send_task("some-task")

    super_apply.assert_called_with(
        "some-task", None, None, headers={"notify_request_id": "1234"}  # name  # args  # kwargs  # other kwargs
    )


def test_send_task_injects_request_id_with_existing_headers(
    mocker,
    notify_celery,
):
    super_apply = mocker.patch("celery.Celery.send_task")
    g.request_id = "1234"

    notify_celery.send_task("some-task", None, None, headers={"something": "else"})  # args  # kwargs  # other kwargs

    super_apply.assert_called_with(
        "some-task",  # name
        None,  # args
        None,  # kwargs
        headers={"notify_request_id": "1234", "something": "else"},  # other kwargs
    )


def test_send_task_injects_request_id_with_none_headers(
    mocker,
    notify_celery,
):
    super_apply = mocker.patch("celery.Celery.send_task")
    g.request_id = "1234"

    notify_celery.send_task(
        "some-task",
        None,  # args
        None,  # kwargs
        headers=None,  # other kwargs (task retry set headers to "None")
    )

    super_apply.assert_called_with(
        "some-task", None, None, headers={"notify_request_id": "1234"}  # name  # args  # kwargs  # other kwargs
    )


def test_send_task_injects_id_from_request(
    mocker,
    notify_celery,
    celery_app,
):
    super_apply = mocker.patch("celery.Celery.send_task")
    request_id_header = celery_app.config["NOTIFY_TRACE_ID_HEADER"]
    request_headers = {request_id_header: "1234"}

    with celery_app.test_request_context(headers=request_headers):
        notify_celery.send_task("some-task")

    super_apply.assert_called_with(
        "some-task", None, None, headers={"notify_request_id": "1234"}  # name  # args  # kwargs  # other kwargs
    )
