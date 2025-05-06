from lxml import etree as ET

from emergency_alerts_utils.xml.common import (
    GOVERNMENT_CHANNEL,
    OPERATOR_CHANNEL,
    SENDER,
    SEVERE_CHANNEL,
    xml_subelement,
)


def generate_ibag_link_test(
    message_number,
    identifier,
    sent,
):
    alert = ET.Element(
        "IBAG_Alert_Attributes",
        attrib={
            "xmlns": "ibag:1.0",
        },
    )

    xml_subelement(alert, "IBAG_protocol_version", text="1.0")
    xml_subelement(alert, "IBAG_sending_gateway_id", text=SENDER)
    xml_subelement(alert, "IBAG_message_number", text=message_number)
    xml_subelement(alert, "IBAG_sent_date_time", text=sent.astimezone().isoformat())
    xml_subelement(alert, "IBAG_status", text="System")
    xml_subelement(alert, "IBAG_message_type", text="Link Test")
    xml_subelement(alert, "IBAG_Digital_Signature", text="")

    return alert


def generate_ibag_alert(
    message_number,
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
        "IBAG_Alert_Attributes",
        attrib={
            "xmlns": "ibag:1.0",
        },
    )

    xml_subelement(alert, "IBAG_protocol_version", text="1.0")
    xml_subelement(alert, "IBAG_sending_gateway_id", text=SENDER)
    xml_subelement(alert, "IBAG_message_number", text=message_number)
    xml_subelement(alert, "IBAG_sender", text=SENDER)
    xml_subelement(alert, "IBAG_sent_date_time", text=sent)
    xml_subelement(alert, "IBAG_status", text="Actual")
    xml_subelement(alert, "IBAG_message_type", text="Alert")
    xml_subelement(alert, "IBAG_cap_alert_uri", text="https://www.gov.uk/alerts")
    xml_subelement(alert, "IBAG_cap_identifier", text=identifier)
    xml_subelement(alert, "IBAG_cap_sent_date_time", text=sent)

    info = xml_subelement(alert, "IBAG_alert_info")

    xml_subelement(info, "IBAG_category", text="Safety")
    xml_subelement(info, "IBAG_event_code", text="LAE")
    xml_subelement(info, "IBAG_severity", text="Severe")
    xml_subelement(info, "IBAG_urgency", text="Expected")
    xml_subelement(info, "IBAG_certainty", text="Likely")
    xml_subelement(info, "IBAG_expires_date_time", text=expires)
    xml_subelement(info, "IBAG_text_language", text=language)
    # length in octets/bytes
    xml_subelement(
        info,
        "IBAG_text_alert_message_length",
        text=str(len(description.encode("utf-8"))),
    )
    xml_subelement(info, "IBAG_text_alert_message", text=description)
    # List of potential channel category values is defined in
    # https://docs.google.com/spreadsheets/d/1UKi18SpfIgaRhmD6iVGaItY-E3MJkxbB/edit#gid=2013248044
    IBAG_channel_category = "4380-CAT5-ENGLISH"
    if channel == OPERATOR_CHANNEL:
        IBAG_channel_category = "4382-CAT7-ENGLISH"
    if channel == SEVERE_CHANNEL:
        IBAG_channel_category = "4378-CAT3-ENGLISH"
    elif channel == GOVERNMENT_CHANNEL:
        IBAG_channel_category = "4370-CAT1-ENGLISH"
    xml_subelement(info, "IBAG_channel_category", text=IBAG_channel_category)

    for i, a in enumerate(areas):
        area = xml_subelement(info, "IBAG_Alert_Area")

        xml_subelement(area, "IBAG_area_description", text="area-{}".format(i + 1))
        xml_subelement(
            area,
            "IBAG_polygon",
            text=" ".join(["{},{}".format(pair[0], pair[1]) for pair in a["polygon"]]),
        )

    xml_subelement(alert, "IBAG_Digital_Signature", text="")

    return alert


def generate_ibag_cancel_message(message_number, identifier, references, sent):
    alert = ET.Element(
        "IBAG_Alert_Attributes",
        attrib={
            "xmlns": "ibag:1.0",
        },
    )

    xml_subelement(alert, "IBAG_protocol_version", text="1.0")
    xml_subelement(alert, "IBAG_sending_gateway_id", text=SENDER)
    xml_subelement(alert, "IBAG_message_number", text=message_number)
    # reference last message in the series
    xml_subelement(alert, "IBAG_referenced_message_number", text=references[-1]["message_number"])
    xml_subelement(
        alert,
        "IBAG_referenced_message_cap_identifier",
        text=references[-1]["message_id"],
    )
    xml_subelement(alert, "IBAG_sender", text=SENDER)
    xml_subelement(alert, "IBAG_sent_date_time", text=sent)
    xml_subelement(alert, "IBAG_status", text="Actual")
    xml_subelement(alert, "IBAG_message_type", text="Cancel")
    xml_subelement(alert, "IBAG_cap_alert_uri", text="https://www.gov.uk/alerts")
    xml_subelement(alert, "IBAG_cap_identifier", text=identifier)
    xml_subelement(alert, "IBAG_cap_sent_date_time", text=sent)
    xml_subelement(alert, "IBAG_Digital_Signature", text="")

    return alert


def format_ibag_signature(xml):
    """
    IBAG message signature needs to be enveloped in a <IBAG_Digital_Signature> child element rather than the root
    element. The empty IBAG_Digital_Signature child element must be included in the pre-signed xml. SignXML appends
    the signature element in the root element so we must move this to the IBAG_Digital_Signature element.
    """
    ns = {"ibag": "ibag:1.0", "ds": "http://www.w3.org/2000/09/xmldsig#"}

    wrapper = xml.xpath("//ibag:IBAG_Digital_Signature", namespaces=ns)[0]
    signature = xml.xpath("/ibag:IBAG_Alert_Attributes/ds:Signature", namespaces=ns)[0]
    wrapper.append(signature)

    return xml
