import datetime
import os

import pytest
import requests_mock
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from flask import Flask
from moto import mock_aws

from emergency_alerts_utils import request_helper


class FakeService:
    id = "1234"


@pytest.fixture
def app():
    flask_app = Flask(__name__)
    ctx = flask_app.app_context()
    ctx.push()

    yield flask_app

    ctx.pop()


@pytest.fixture
def celery_app(mocker):
    app = Flask(__name__)
    app.config["CELERY"] = {"broker_url": "foo"}
    app.config["NOTIFY_TRACE_ID_HEADER"] = "Ex-Notify-Request-Id"
    request_helper.init_app(app)

    ctx = app.app_context()
    ctx.push()

    yield app
    ctx.pop()


@pytest.fixture(scope="session")
def sample_service():
    return FakeService()


@pytest.fixture
def rmock():
    with requests_mock.mock() as rmock:
        yield rmock


@pytest.fixture
def os_environ():
    """
    clear os.environ, and restore it after the test runs
    """
    old_env = os.environ.copy()
    os.environ.clear()
    yield
    for k, v in old_env.items():
        os.environ[k] = v


@pytest.fixture(scope="function")
def mocked_aws(os_environ):
    """
    An alternative to the moto @mock_aws decorator - ensuring any environment variables
    do not interfere with the AWS client instead of reaching moto.
    """
    os.environ["AWS_ACCESS_KEY_ID"] = "mocked"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "mocked"
    os.environ["AWS_SECURITY_TOKEN"] = "mocked"
    os.environ["AWS_SESSION_TOKEN"] = "mocked"
    os.environ["AWS_DEFAULT_REGION"] = "eu-west-2"

    with mock_aws():
        yield


@pytest.fixture
def test_cert():
    key = rsa.generate_private_key(65537, 2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(datetime.datetime.now(datetime.UTC))
        .not_valid_after(datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )

    key = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    cert = cert.public_bytes(serialization.Encoding.PEM)
    return key, cert
