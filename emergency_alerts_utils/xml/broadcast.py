import datetime
import logging

import dateutil.tz

from emergency_alerts_utils.xml.cap import (
    generate_cap_alert,
    generate_cap_cancel_message,
    generate_cap_link_test,
)
from emergency_alerts_utils.xml.common import (
    ALERT_MESSAGE_TYPE,
    CANCEL_MESSAGE_TYPE,
    IBAG_MESSAGE_FORMAT,
    TEST_MESSAGE_TYPE,
    convert_etree_to_string,
    digitally_sign,
    validate_channel,
    validate_message_format,
    validate_message_type,
)
from emergency_alerts_utils.xml.ibag import (
    format_ibag_signature,
    generate_ibag_alert,
    generate_ibag_cancel_message,
    generate_ibag_link_test,
)

logger = logging.getLogger("broadcast")


def generate_xml_body(event, signing_enabled=False, signing_key=None, signing_certificate=None):  # noqa: C901
    # C901: Too complex - but this method was migrated from CBC proxy as-is

    identifier = event["identifier"]

    message_format = validate_message_format(event["message_format"])
    message_type = validate_message_type(event["message_type"])

    body = None

    if message_type == TEST_MESSAGE_TYPE:
        tz = dateutil.tz.gettz("UTC")
        sent = datetime.datetime.now()
        sent = sent.replace(second=0, microsecond=0, tzinfo=tz)
        if message_format == IBAG_MESSAGE_FORMAT:
            xml = generate_ibag_link_test(
                message_number=event["message_number"],
                identifier=identifier,
                sent=sent,
            )
        else:
            xml = generate_cap_link_test(
                identifier=identifier,
                sent=sent,
            )

    elif message_type == ALERT_MESSAGE_TYPE:
        channel = validate_channel(event["channel"])
        if message_format == IBAG_MESSAGE_FORMAT:
            xml = generate_ibag_alert(
                message_number=event["message_number"],
                identifier=identifier,
                headline=event["headline"],
                description=event["description"],
                areas=event["areas"],
                sent=event["sent"],
                expires=event["expires"],
                language=event["language"],
                channel=channel,
            )
        else:
            xml = generate_cap_alert(
                identifier=identifier,
                headline=event["headline"],
                description=event["description"],
                areas=event["areas"],
                sent=event["sent"],
                expires=event["expires"],
                language=event["language"],
                channel=channel,
                web=event.get("web", None)
            )

    elif message_type == CANCEL_MESSAGE_TYPE:
        if message_format == IBAG_MESSAGE_FORMAT:
            xml = generate_ibag_cancel_message(
                message_number=event["message_number"],
                identifier=identifier,
                references=event["references"],
                sent=event["sent"],
            )
        else:
            xml = generate_cap_cancel_message(
                identifier=identifier,
                references=event["references"],
                sent=event["sent"],
            )

    if signing_enabled:
        xml = digitally_sign(xml, key=signing_key, cert=signing_certificate)
        if message_format == IBAG_MESSAGE_FORMAT:
            xml = format_ibag_signature(xml)

    body = convert_etree_to_string(xml)
    logger.info("Body: " + body)
    return body
