# We use lxml in place of native xml to support consistent encoding/decoding,
# handling of namespaces and for securely parsing untrusted XML
from lxml import etree as ET

from emergency_alerts_utils.xml.common import (
    GOVERNMENT_CHANNEL,
    OPERATOR_CHANNEL,
    SENDER,
    SEVERE_CHANNEL,
    xml_subelement,
)


def generate_cap_link_test(
    identifier,
    sent,
):
    alert = ET.Element(
        "alert",
        attrib={
            "xmlns": "urn:oasis:names:tc:emergency:cap:1.2",
        },
    )

    xml_subelement(alert, "identifier", text=identifier)
    xml_subelement(alert, "sender", text=SENDER)
    xml_subelement(alert, "sent", text=sent.astimezone().isoformat())
    xml_subelement(alert, "status", text="Test")
    xml_subelement(alert, "msgType", text="Alert")
    xml_subelement(alert, "scope", text="Public")

    return alert


def generate_cap_alert(
    identifier,
    headline,
    description,
    areas,
    sent,
    expires,
    language,
    channel,
):
    alert = ET.Element(
        "alert",
        attrib={
            "xmlns": "urn:oasis:names:tc:emergency:cap:1.2",
        },
    )

    xml_subelement(alert, "identifier", text=identifier)
    xml_subelement(alert, "sender", text=SENDER)
    xml_subelement(alert, "sent", text=sent)
    xml_subelement(alert, "status", text="Actual")
    xml_subelement(alert, "msgType", text="Alert")
    xml_subelement(alert, "scope", text="Public")

    info = xml_subelement(alert, "info")

    xml_subelement(info, "language", text=language)
    xml_subelement(info, "category", text="Safety")
    cap_event = "RMT"
    if channel == OPERATOR_CHANNEL:
        cap_event = "OPR"
    if channel == SEVERE_CHANNEL:
        cap_event = "Alert"
    elif channel == GOVERNMENT_CHANNEL:
        cap_event = "EAN"
    xml_subelement(info, "event", text=cap_event)
    xml_subelement(info, "urgency", text="Expected")
    xml_subelement(info, "severity", text="Severe")
    xml_subelement(info, "certainty", text="Likely")
    xml_subelement(info, "expires", text=expires)
    xml_subelement(info, "senderName", text="GOV.UK Emergency Alerts")
    xml_subelement(info, "headline", text=headline)
    xml_subelement(info, "description", text=description)

    for i, a in enumerate(areas):
        area = xml_subelement(info, "area")

        xml_subelement(area, "areaDesc", text="area-{}".format(i + 1))
        xml_subelement(
            area,
            "polygon",
            text=" ".join(["{},{}".format(pair[0], pair[1]) for pair in a["polygon"]]),
        )

    return alert


def generate_cap_cancel_message(identifier, sent, references):
    alert = ET.Element(
        "alert",
        attrib={
            "xmlns": "urn:oasis:names:tc:emergency:cap:1.2",
        },
    )

    references_list = [f"{SENDER},{ref['message_id']},{ref['sent']}" for ref in references]
    references_string = " ".join(references_list)

    xml_subelement(alert, "identifier", text=identifier)
    xml_subelement(alert, "sender", text=SENDER)
    xml_subelement(alert, "sent", text=sent)
    xml_subelement(alert, "status", text="Actual")
    xml_subelement(alert, "msgType", text="Cancel")
    xml_subelement(alert, "scope", text="Public")
    xml_subelement(alert, "references", text=references_string)

    return alert


def convert_utc_datetime_to_cap_standard_string(dt):
    """
    As defined in section 3.3.2 of
    http://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2-os.html
    They define the standard "YYYY-MM-DDThh:mm:ssXzh:zm", where X is
    `+` if the timezone is > UTC, otherwise `-`

    No validation of the provided datetime is performed. It must be in UTC.
    """
    return f"{dt.strftime('%Y-%m-%dT%H:%M:%S')}-00:00"
