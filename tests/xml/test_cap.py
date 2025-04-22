import datetime
import os
import uuid

import dateutil.tz
import pytest
from lxml import etree

from emergency_alerts_utils.xml.broadcast import generate_xml_body
from emergency_alerts_utils.xml.cap import (
    generate_cap_alert,
    generate_cap_cancel_message,
    generate_cap_link_test,
)

LINK_TEST_CAP_EVENT = {
    "identifier": str(uuid.uuid4()),
    "message_type": "test",
    "message_format": "cap",
}

ALERT_CAP_EVENT = {
    "identifier": str(uuid.uuid4()),
    "message_type": "alert",
    "message_format": "cap",
    "headline": "my-headline",
    "description": "  description\nwith\nnewlines",
    "language": "English",
    "areas": [
        {
            "polygon": [
                [51.12, -1.2],
                [51.12, 1.2],
                [51.74, 1.2],
                [51.74, -1.2],
                [51.12, -1.2],
            ],
        }
    ],
    "sent": "2020-01-01T00:00:00-00:00",
    "expires": "2020-01-01T00:00:00-00:00",
    "channel": "severe",
    "cbc_target": "cbc_a",
}

CANCEL_CAP_EVENT = {
    "identifier": str(uuid.uuid4()),
    "message_type": "cancel",
    "message_format": "cap",
    "sent": "2020-01-01T00:00:00-01:00",
    "references": [
        {
            "message_id": str(uuid.uuid4()),
            "message_number": "0000004e",
            "sent": "2020-12-08 11:19:44.130585",
        },
        {
            "message_id": str(uuid.uuid4()),
            "message_number": "0000007b",
            "sent": "2020-12-09 10:10:42.120561",
        },
    ],
}


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


def xml_path(alert_xml, path, format="cap"):
    root = etree.fromstring(etree.tostring(alert_xml, encoding="unicode"))

    if format == "cap":
        ns = {
            "cap": "urn:oasis:names:tc:emergency:cap:1.2",
            "ds": "http://www.w3.org/2000/09/xmldsig#",
        }
    else:
        ns = {
            "ibag": "ibag:1.0",
            "ds": "http://www.w3.org/2000/09/xmldsig#",
        }

    return root.xpath(path, namespaces=ns)


@pytest.mark.parametrize(
    "channel, expected_event",
    [
        ["test", "RMT"],
        ["operator", "OPR"],
        ["severe", "Alert"],
        ["government", "EAN"],
    ],
)
def test_cap_alert_creation(channel, expected_event):
    tz = dateutil.tz.gettz("UTC")

    sent = datetime.datetime.now()
    sent = sent.replace(second=0, microsecond=0, tzinfo=tz)
    sent = sent.astimezone().isoformat()

    expires = datetime.datetime.now() + datetime.timedelta(minutes=5)
    expires = expires.replace(second=0, microsecond=0, tzinfo=tz)
    expires = expires.astimezone().isoformat()

    headline = "my-headline"
    description = "this is an alert description"
    identifier = str(uuid.uuid4())

    # a single area which is a square including london
    areas = [
        {
            "polygon": [
                [51.12, -1.2],
                [51.12, 1.2],
                [51.74, 1.2],
                [51.74, -1.2],
                [51.12, -1.2],
            ],
        }
    ]

    alert_body = generate_cap_alert(
        description=description,
        headline=headline,
        identifier=identifier,
        areas=areas,
        sent=sent,
        expires=expires,
        language="en-GB",
        channel=channel,
    )

    assert_valid_cap_xml(alert_body)

    assert xml_path(
        alert_body,
        "/cap:alert/cap:identifier//text()",
    ) == [identifier]

    assert xml_path(
        alert_body,
        "/cap:alert/cap:status//text()",
    ) == ["Actual"]

    assert xml_path(
        alert_body,
        "/cap:alert/cap:sent//text()",
    ) == [sent]

    assert xml_path(
        alert_body,
        "/cap:alert/cap:info/cap:language//text()",
    ) == ["en-GB"]

    assert xml_path(
        alert_body,
        "/cap:alert/cap:info/cap:expires//text()",
    ) == [expires]

    assert xml_path(
        alert_body,
        "/cap:alert/cap:info/cap:headline//text()",
    ) == [headline]

    assert xml_path(
        alert_body,
        "/cap:alert/cap:info/cap:description//text()",
    ) == [description]

    assert xml_path(
        alert_body,
        "/cap:alert/cap:info/cap:area/cap:areaDesc//text()",
    ) == ["area-1"]

    assert xml_path(
        alert_body,
        "/cap:alert/cap:info/cap:area/cap:polygon//text()",
    ) == ["51.12,-1.2 51.12,1.2 51.74,1.2 51.74,-1.2 51.12,-1.2"]

    assert xml_path(
        alert_body,
        "/cap:alert/cap:info/cap:event//text()",
    ) == [expected_event]

    assert xml_path(
        alert_body,
        "/cap:alert/cap:info/cap:urgency//text()",
    ) == ["Expected"]

    assert xml_path(
        alert_body,
        "/cap:alert/cap:info/cap:severity//text()",
    ) == ["Severe"]

    assert xml_path(
        alert_body,
        "/cap:alert/cap:info/cap:certainty//text()",
    ) == ["Likely"]


def test_generate_cap_cancel_message():
    timezone = dateutil.tz.gettz("UTC")

    sent = datetime.datetime.now()
    sent = sent.replace(second=0, microsecond=0, tzinfo=timezone)
    sent = sent.astimezone().isoformat()

    identifier = str(uuid.uuid4())

    ref_message_1_id = str(uuid.uuid4())
    ref_message_2_id = str(uuid.uuid4())

    references = [
        {
            "message_id": ref_message_1_id,
            "message_number": "0000004e",
            "sent": "2020-12-08 11:19:44.130585",
        },
        {
            "message_id": ref_message_2_id,
            "message_number": "0000007b",
            "sent": "2020-12-09 10:10:42.120561",
        },
    ]

    alert_body = generate_cap_cancel_message(identifier=identifier, sent=sent, references=references)

    assert_valid_cap_xml(alert_body)

    assert xml_path(
        alert_body,
        "/cap:alert/cap:identifier//text()",
    ) == [identifier]

    assert xml_path(
        alert_body,
        "/cap:alert/cap:status//text()",
    ) == ["Actual"]

    assert xml_path(
        alert_body,
        "/cap:alert/cap:sent//text()",
    ) == [sent]

    assert xml_path(
        alert_body,
        "/cap:alert/cap:msgType//text()",
    ) == ["Cancel"]

    assert xml_path(
        alert_body,
        "/cap:alert/cap:references//text()",
    ) == [
        (
            f"broadcasts@notifications.service.gov.uk,{ref_message_1_id},2020-12-08 11:19:44.130585"
            f" broadcasts@notifications.service.gov.uk,{ref_message_2_id},2020-12-09 10:10:42.120561"
        )
    ]


@pytest.mark.parametrize(
    "language",
    [
        pytest.param("en-GB"),
        pytest.param("cy-GB"),
        # The CAP XSD has no schema for the language property, thus we can't test negative cases here like with IBAG
    ],
)
def test_cap_alert_creation_with_language(language):
    tz = dateutil.tz.gettz("UTC")

    sent = datetime.datetime.now()
    sent = sent.replace(second=0, microsecond=0, tzinfo=tz)
    sent = sent.astimezone().isoformat()

    expires = datetime.datetime.now() + datetime.timedelta(minutes=5)
    expires = expires.replace(second=0, microsecond=0, tzinfo=tz)
    expires = expires.astimezone().isoformat()

    headline = "my-headline"
    identifier = str(uuid.uuid4())
    areas = [{"polygon": []}]
    description = "English or Welsh"

    alert_body = generate_cap_alert(
        description=description,
        headline=headline,
        identifier=identifier,
        areas=areas,
        sent=sent,
        expires=expires,
        language=language,
        channel="test",
    )

    assert_valid_cap_xml(alert_body)

    assert xml_path(
        alert_body,
        "/cap:alert/cap:info/cap:language//text()",
    ) == [language]

    assert xml_path(
        alert_body,
        "/cap:alert/cap:info/cap:description//text()",
    ) == [description]


def test_alert_creation_escapes_description():
    tz = dateutil.tz.gettz("UTC")

    sent = datetime.datetime.now()
    sent = sent.replace(second=0, microsecond=0, tzinfo=tz)
    sent = sent.astimezone().isoformat()

    expires = datetime.datetime.now() + datetime.timedelta(minutes=5)
    expires = expires.replace(second=0, microsecond=0, tzinfo=tz)
    expires = expires.astimezone().isoformat()

    headline = "my-headline"
    identifier = str(uuid.uuid4())
    areas = [{"polygon": []}]

    description = "<>< i am a fish"

    alert_body = generate_cap_alert(
        description=description,
        headline=headline,
        identifier=identifier,
        areas=areas,
        sent=sent,
        expires=expires,
        language="en-GB",
        channel="severe",
    )

    assert_valid_cap_xml(alert_body)

    assert xml_path(
        alert_body,
        "/cap:alert/cap:info/cap:description//text()",
    ) == [description]


def test_cap_link_test_creation():
    tz = dateutil.tz.gettz("UTC")

    sent = datetime.datetime.now()
    sent = sent.replace(second=0, microsecond=0, tzinfo=tz)

    identifier = str(uuid.uuid4())

    link_test_body = generate_cap_link_test(identifier=identifier, sent=sent)

    assert_valid_cap_xml(link_test_body)

    assert xml_path(
        link_test_body,
        "/cap:alert/cap:identifier//text()",
    ) == [identifier]

    assert xml_path(
        link_test_body,
        "/cap:alert/cap:status//text()",
    ) == ["Test"]

    assert xml_path(
        link_test_body,
        "/cap:alert/cap:sent//text()",
    ) == [sent.astimezone().isoformat()]


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
