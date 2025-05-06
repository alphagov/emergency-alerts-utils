import uuid

from lxml import etree

LINK_TEST_IBAG_EVENT = {
    "identifier": str(uuid.uuid4()),
    "message_type": "test",
    "message_format": "ibag",
    "message_number": "00000073",
}

ALERT_IBAG_EVENT = {
    "identifier": str(uuid.uuid4()),
    "message_type": "alert",
    "message_format": "ibag",
    "message_number": "00000074",
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
}

CANCEL_IBAG_EVENT = {
    "identifier": str(uuid.uuid4()),
    "message_type": "cancel",
    "message_format": "ibag",
    "message_number": "00000075",
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
