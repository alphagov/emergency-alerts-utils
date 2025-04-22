import os

import pytest
from lxml import etree
from signxml import XMLVerifier

from emergency_alerts_utils.xml.broadcast import generate_xml_body
from emergency_alerts_utils.xml.common import (
    digitally_sign,
    validate_channel,
    validate_message_format,
    validate_message_type,
)
from tests.xml.utils import (  # noqa: F401 - events are eval-ed by tests
    ALERT_CAP_EVENT,
    ALERT_IBAG_EVENT,
    CANCEL_CAP_EVENT,
    CANCEL_IBAG_EVENT,
    LINK_TEST_CAP_EVENT,
    LINK_TEST_IBAG_EVENT,
)


def assert_valid_xmldsig(sig_xml):
    xmldsig_path = os.path.join(
        os.path.dirname(__file__),
        "xmldsig.xsd",
    )

    xml_parser = etree.XMLParser(
        ns_clean=True,
        recover=True,
        encoding="utf-8",
    )

    xmldsig_schema = etree.XMLSchema(file=xmldsig_path)

    xmldsig_doc = etree.fromstring(sig_xml.encode("utf-8"), parser=xml_parser)

    xmldsig_schema.assertValid(xmldsig_doc)


def test_validate_message_format_capitalises_message_format():
    assert [validate_message_format(f) for f in ("ibag", "cap")] == [
        "IBAG",
        "CAP",
    ]


def test_validate_message_format_raises_key_error_for_unknown_type():
    with pytest.raises(KeyError) as e:
        validate_message_format("bad")
        assert isinstance(e, KeyError)


def test_validate_message_type_capitalises_message_type():
    assert [validate_message_type(t) for t in ("alert", "update", "cancel", "test")] == [
        "Alert",
        "Update",
        "Cancel",
        "Test",
    ]


def test_validate_message_type_raises_key_error_for_unknown_type():
    with pytest.raises(KeyError) as e:
        validate_message_type("bad")
        assert isinstance(e, KeyError)


@pytest.mark.parametrize("channel", ["test", "severe", "government", "operator"])
def test_validate_channel_allows_known_channel(channel):
    assert channel == validate_channel(channel)


def test_validate_channel_raises_exception_for_unknown_channel():
    with pytest.raises(AssertionError):
        validate_channel("unknown")


def test_generate_xml_body_doesnt_canonicalize():
    body = generate_xml_body(ALERT_CAP_EVENT)

    path = "/cap:alert/cap:info/cap:description//text()"
    description = etree.fromstring(body).xpath(path, namespaces={"cap": "urn:oasis:names:tc:emergency:cap:1.2"})[0]
    assert description == "  description\nwith\nnewlines"


@pytest.mark.parametrize(
    "message_type, expected_type, expected_status",
    [
        ["ALERT", "Alert", "Actual"],
        ["CANCEL", "Cancel", "Actual"],
        ["LINK_TEST", "Alert", "Test"],
    ],
)
def test_generate_xml_body_chooses_right_flow_for_message_type_and_format_cap(
    message_type, expected_type, expected_status
):
    event = eval(f"{message_type}_CAP_EVENT")
    body = generate_xml_body(event)

    type_path = "/cap:alert/cap:msgType//text()"
    type = etree.fromstring(body).xpath(type_path, namespaces={"cap": "urn:oasis:names:tc:emergency:cap:1.2"})[0]
    assert type == expected_type

    status_path = "/cap:alert/cap:status//text()"
    status = etree.fromstring(body).xpath(status_path, namespaces={"cap": "urn:oasis:names:tc:emergency:cap:1.2"})[0]
    assert status == expected_status


@pytest.mark.parametrize(
    "message_type, expected_type, expected_status",
    [
        ["ALERT", "Alert", "Actual"],
        ["CANCEL", "Cancel", "Actual"],
        ["LINK_TEST", "Link Test", "System"],
    ],
)
def test_generate_xml_body_chooses_right_flow_for_message_type_and_format_ibag(
    message_type, expected_type, expected_status
):
    event = eval(f"{message_type}_IBAG_EVENT")

    body = generate_xml_body(event)

    type_path = "/ibag:IBAG_Alert_Attributes/ibag:IBAG_message_type//text()"
    type = etree.fromstring(body).xpath(type_path, namespaces={"ibag": "ibag:1.0"})[0]
    assert type == expected_type

    status_path = "/ibag:IBAG_Alert_Attributes/ibag:IBAG_status//text()"
    status = etree.fromstring(body).xpath(status_path, namespaces={"ibag": "ibag:1.0"})[0]
    assert status == expected_status


def test_message_signature_is_valid(mocker):
    data_to_sign = "<Test><Child>Some Value</Child></Test>"
    key = open(os.path.join(os.path.dirname(__file__), "example.key")).read()
    cert = open(os.path.join(os.path.dirname(__file__), "example.pem")).read()

    root = etree.fromstring(data_to_sign)
    signed_xml = digitally_sign(root, key=key, cert=cert)

    signature = XMLVerifier().verify(signed_xml, x509_cert=cert).signature_xml
    assert_valid_xmldsig(etree.tostring(signature, encoding="unicode"))


def test_signed_cap_message_is_valid(mocker):
    key = open(os.path.join(os.path.dirname(__file__), "example.key")).read()
    cert = open(os.path.join(os.path.dirname(__file__), "example.pem")).read()

    xml_root = generate_xml_body(ALERT_CAP_EVENT, signing_enabled=True, signing_key=key, signing_certificate=cert)
    assert_valid_cap_xml(etree.fromstring(xml_root))


def assert_valid_cap_xml(cap_alert_xml):
    cap_alert_xml = etree.tostring(cap_alert_xml)
    cap12_path = os.path.join(
        os.path.dirname(__file__),
        "cap12.xsd",
    )

    xml_parser = etree.XMLParser(
        ns_clean=True,
        recover=True,
        encoding="utf-8",
    )

    cap_alert_schema = etree.XMLSchema(file=cap12_path)

    cap_alert_doc = etree.fromstring(cap_alert_xml, parser=xml_parser)

    cap_alert_schema.assertValid(cap_alert_doc)
