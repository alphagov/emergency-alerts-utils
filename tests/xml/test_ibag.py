import datetime
import os
import uuid

import dateutil.tz
import pytest
from lxml import etree

from emergency_alerts_utils.xml.broadcast import generate_xml_body
from emergency_alerts_utils.xml.common import SENDER
from emergency_alerts_utils.xml.ibag import (
    generate_ibag_alert,
    generate_ibag_cancel_message,
    generate_ibag_link_test,
)
from tests.xml.utils import ALERT_IBAG_EVENT, xml_path


def assert_valid_ibag_xml(ibag_alert_xml):
    ibag_alert_xml = etree.tostring(ibag_alert_xml, encoding="utf-8")
    xsd_path = os.path.join(
        os.path.dirname(__file__),
        "ibag10.xsd",
    )

    xml_parser = etree.XMLParser(
        ns_clean=True,
        recover=True,
        encoding="utf-8",
    )

    ibag_alert_schema = etree.XMLSchema(file=xsd_path)

    ibag_alert_doc = etree.fromstring(ibag_alert_xml, parser=xml_parser)

    ibag_alert_schema.assertValid(ibag_alert_doc)


@pytest.mark.parametrize(
    "channel, expected_IBAG_channel_category",
    [
        ["test", "4380-CAT5-ENGLISH"],
        ["operator", "4382-CAT7-ENGLISH"],
        ["severe", "4378-CAT3-ENGLISH"],
        ["government", "4370-CAT1-ENGLISH"],
    ],
)
def test_ibag_alert_creation(channel, expected_IBAG_channel_category):
    tz = dateutil.tz.gettz("UTC")

    sent = datetime.datetime.now()
    sent = sent.replace(second=0, microsecond=0, tzinfo=tz)
    sent = sent.astimezone().isoformat()

    expires = datetime.datetime.now() + datetime.timedelta(minutes=5)
    expires = expires.replace(second=0, microsecond=0, tzinfo=tz)
    expires = expires.astimezone().isoformat()

    headline = "my-headline"
    description = "this is an alert description"
    message_length = len(description)
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

    alert_body = generate_ibag_alert(
        message_number="00000090",
        description=description,
        headline=headline,
        identifier=identifier,
        areas=areas,
        sent=sent,
        expires=expires,
        language="English",
        channel=channel,
    )

    assert_valid_ibag_xml(alert_body)

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_sending_gateway_id//text()",
        "ibag",
    ) == [SENDER]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_message_number//text()",
        "ibag",
    ) == ["00000090"]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_sender//text()",
        "ibag",
    ) == [SENDER]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_sent_date_time//text()",
        "ibag",
    ) == [sent]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_status//text()",
        "ibag",
    ) == ["Actual"]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_message_type//text()",
        "ibag",
    ) == ["Alert"]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_cap_alert_uri//text()",
        "ibag",
    ) == ["https://www.gov.uk/alerts"]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_text_language//text()",
        "ibag",
    ) == ["English"]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_expires_date_time//text()",
        "ibag",
    ) == [expires]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_text_alert_message//text()",
        "ibag",
    ) == [description]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_text_alert_message_length//text()",
        "ibag",
    ) == [str(message_length)]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_Alert_Area[1]/ibag:IBAG_area_description//text()",
        "ibag",
    ) == ["area-1"]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_Alert_Area[1]/ibag:IBAG_polygon//text()",
        "ibag",
    ) == ["51.12,-1.2 51.12,1.2 51.74,1.2 51.74,-1.2 51.12,-1.2"]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_channel_category//text()",
        "ibag",
    ) == [expected_IBAG_channel_category]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_severity//text()",
        "ibag",
    ) == ["Severe"]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_urgency//text()",
        "ibag",
    ) == ["Expected"]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_certainty//text()",
        "ibag",
    ) == ["Likely"]


def test_generate_ibag_cancel_message():
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

    alert_body = generate_ibag_cancel_message(
        message_number="00000090",
        identifier=identifier,
        references=references,
        sent=sent,
    )

    assert_valid_ibag_xml(alert_body)

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_sending_gateway_id//text()",
        "ibag",
    ) == [SENDER]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_message_number//text()",
        "ibag",
    ) == ["00000090"]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_referenced_message_number//text()",
        "ibag",
    ) == ["0000007b"]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_referenced_message_cap_identifier//text()",
        "ibag",
    ) == [ref_message_2_id]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_message_type//text()",
        "ibag",
    ) == ["Cancel"]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_sender//text()",
        "ibag",
    ) == [SENDER]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_sent_date_time//text()",
        "ibag",
    ) == [sent]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_status//text()",
        "ibag",
    ) == ["Actual"]


@pytest.mark.parametrize(
    "language",
    [
        pytest.param("English"),
        pytest.param("Welsh"),
        pytest.param(
            "en-GB",
            marks=pytest.mark.xfail(reason="IBAG should not accept CAP-formatted languages"),
        ),
        pytest.param(
            "cy-GB",
            marks=pytest.mark.xfail(reason="IBAG should not accept CAP-formatted languages"),
        ),
    ],
)
def test_ibag_alert_creation_with_language(language):
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

    alert_body = generate_ibag_alert(
        message_number="00000090",
        description=description,
        headline=headline,
        identifier=identifier,
        areas=areas,
        sent=sent,
        expires=expires,
        language=language,
        channel="severe",
    )

    assert_valid_ibag_xml(alert_body)

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_text_language//text()",
        "ibag",
    ) == [language]

    assert xml_path(
        alert_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_text_alert_message//text()",
        "ibag",
    ) == [description]


def test_ibag_link_test_creation():
    tz = dateutil.tz.gettz("UTC")

    sent = datetime.datetime.now()
    sent = sent.replace(second=0, microsecond=0, tzinfo=tz)

    identifier = str(uuid.uuid4())

    link_test_body = generate_ibag_link_test(message_number="00000090", identifier=identifier, sent=sent)

    assert_valid_ibag_xml(link_test_body)

    assert xml_path(
        link_test_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_message_number//text()",
        "ibag",
    ) == ["00000090"]

    assert xml_path(
        link_test_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_sent_date_time//text()",
        "ibag",
    ) == [sent.astimezone().isoformat()]

    assert xml_path(
        link_test_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_status//text()",
        "ibag",
    ) == ["System"]

    assert xml_path(
        link_test_body,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_message_type//text()",
        "ibag",
    ) == ["Link Test"]


def test_format_ibag_signature_moves_the_signature_to_a_child_element(mocker):
    key = open(os.path.join(os.path.dirname(__file__), "example.key")).read()
    cert = open(os.path.join(os.path.dirname(__file__), "example.pem")).read()

    xml_root = etree.fromstring(
        generate_xml_body(
            ALERT_IBAG_EVENT,
            signing_enabled=True,
            signing_key=key,
            signing_certificate=cert,
        )
    )

    assert xml_path(
        xml_root,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_Digital_Signature/ds:Signature",
        "ibag",
    )


def test_signed_ibag_message_is_valid(mocker):
    key = open(os.path.join(os.path.dirname(__file__), "example.key")).read()
    cert = open(os.path.join(os.path.dirname(__file__), "example.pem")).read()

    xml_root = generate_xml_body(
        ALERT_IBAG_EVENT,
        signing_enabled=True,
        signing_key=key,
        signing_certificate=cert,
    )
    assert_valid_ibag_xml(etree.fromstring(xml_root))
