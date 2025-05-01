# Shared utilties and constants between CAP and IBAG broadcast formats

from lxml import etree as ET
from signxml import XMLSigner

ALERT_MESSAGE_TYPE = "Alert"
UPDATE_MESSAGE_TYPE = "Update"
CANCEL_MESSAGE_TYPE = "Cancel"
TEST_MESSAGE_TYPE = "Test"

IBAG_MESSAGE_FORMAT = "IBAG"
CAP_MESSAGE_FORMAT = "CAP"

TEST_CHANNEL = "test"
OPERATOR_CHANNEL = "operator"
SEVERE_CHANNEL = "severe"
GOVERNMENT_CHANNEL = "government"
# Channels we allow the user to request the broadcast is sent on. We will then transform
# these into the XML needed to get sent on the 4380 RMT test channel, the 4382 operator
# channel the 4378 severe channel or the 4370 government channel.
#
# This won't allow the choice of any of the test, operator, severe or government channels
# (there are multiple) but instead to go out on one of the four channels we've configured.
ALLOWED_CHANNELS = [TEST_CHANNEL, OPERATOR_CHANNEL, SEVERE_CHANNEL, GOVERNMENT_CHANNEL]

SENDER = "broadcasts@notifications.service.gov.uk"

HEADLINE = "GOV.UK Emergency Alert"


def digitally_sign(xml, key, cert):
    """
    Given an xml etree, envelopes a Signature block to the root element, that consists of a digital signature based on
    https://www.ietf.org/rfc/rfc4051.txt. Canonicalizes the element using xml-c14n11, and then signs that, then returns
    the xml etree with that signature in place.
    """
    signed_root = XMLSigner(
        signature_algorithm="rsa-sha256",
        digest_algorithm="sha256",
        c14n_algorithm="http://www.w3.org/2006/12/xml-c14n11",
    ).sign(xml, key=key, cert=cert)

    return signed_root


def xml_subelement(elem, name, attrib=None, text=None):
    if attrib is None:
        attrib = {}

    sub = ET.SubElement(elem, name, attrib=attrib)

    if text is not None:
        sub.text = text

    return sub


def convert_etree_to_string(xml):
    """
    Currently doesn't canonicalise it, as we believe this may be causing issues with line breaks in the description
    that users see.
    """
    return ET.tostring(xml, encoding="unicode")


def validate_message_format(message_format):
    """validates the message format to be sent to the CBC"""

    return {
        "ibag": IBAG_MESSAGE_FORMAT,
        "cap": CAP_MESSAGE_FORMAT,
    }[message_format.lower()]


def validate_message_type(message_type):
    """validate_message_type returns a KeyError if the alert type is not recognised"""

    return {
        "alert": ALERT_MESSAGE_TYPE,
        "update": UPDATE_MESSAGE_TYPE,
        "cancel": CANCEL_MESSAGE_TYPE,
        "test": TEST_MESSAGE_TYPE,
    }[message_type.lower()]


def validate_channel(channel):
    """validate_channel asserts if the channel is not recognised"""
    if channel not in ALLOWED_CHANNELS:
        raise AssertionError(f"'{channel}' is not an allowed channel. Must be in {ALLOWED_CHANNELS}")
    return channel
