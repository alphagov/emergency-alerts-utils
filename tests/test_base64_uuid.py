import os
from uuid import UUID

import pytest

from emergency_alerts_utils.base64_uuid import (
    base64_to_bytes,
    base64_to_uuid,
    bytes_to_base64,
    uuid_to_base64,
)


def test_bytes_to_base64_to_bytes():
    b = os.urandom(32)
    b64 = bytes_to_base64(b)
    assert base64_to_bytes(b64) == b


@pytest.mark.parametrize(
    "url_val",
    [
        "AAAAAAAAAAAAAAAAAAAAAQ",
        "AAAAAAAAAAAAAAAAAAAAAQ=",  # even though this has invalid padding we put extra =s on the end so this is okay
        "AAAAAAAAAAAAAAAAAAAAAQ==",
    ],
)
def test_base64_converter_to_python(url_val):
    assert base64_to_uuid(url_val) == UUID(int=1)


@pytest.mark.parametrize("python_val", [UUID(int=1), "00000000-0000-0000-0000-000000000001"])
def test_base64_converter_to_url(python_val):
    assert uuid_to_base64(python_val) == "AAAAAAAAAAAAAAAAAAAAAQ"


@pytest.mark.parametrize(
    "url_val, expected_response",
    [
        (
            "this_is_valid_base64_but_is_too_long_to_be_a_uuid",
            "Invalid base64-encoded string",
        ),
        (
            "this_one_has_emoji_➕➕➕",
            "codec can't encode characters",
        ),
    ],
)
def test_base64_converter_to_python_raises_validation_error(url_val, expected_response):
    with pytest.raises(Exception, match=expected_response):
        base64_to_uuid(url_val)


def test_base64_converter_to_url_raises_validation_error():
    with pytest.raises(Exception, match="object has no attribute 'replace'"):
        uuid_to_base64(object())
