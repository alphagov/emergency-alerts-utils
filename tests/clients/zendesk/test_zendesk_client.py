import pytest

from emergency_alerts_utils.clients.zendesk.zendesk_client import (
    EASSupportTicket,
    ZendeskClient,
    ZendeskError,
)


@pytest.fixture(scope="function")
def zendesk_client(app):
    client = ZendeskClient()

    app.config["ZENDESK_API_KEY"] = "testkey"

    client.init_app(app)

    return client


def test_zendesk_client_send_ticket_to_zendesk(zendesk_client, app, mocker, rmock):
    rmock.request(
        "POST",
        ZendeskClient.ZENDESK_TICKET_URL,
        status_code=201,
        json={
            "ticket": {
                "id": 12345,
                "subject": "Something is wrong",
            }
        },
    )
    mock_logger = mocker.patch.object(app.logger, "info")

    ticket = EASSupportTicket("subject", "message", "incident")
    zendesk_client.send_ticket_to_zendesk(ticket)

    assert rmock.last_request.headers["Authorization"][:6] == "Basic "
    assert rmock.last_request.json() == ticket.request_data
    mock_logger.assert_called_once_with("Zendesk create ticket 12345 succeeded")


def test_zendesk_client_send_ticket_to_zendesk_error(zendesk_client, app, mocker, rmock):
    rmock.request("POST", ZendeskClient.ZENDESK_TICKET_URL, status_code=401, json={"foo": "bar"})

    mock_logger = mocker.patch.object(app.logger, "error")

    ticket = EASSupportTicket("subject", "message", "incident")

    with pytest.raises(ZendeskError):
        zendesk_client.send_ticket_to_zendesk(ticket)

    mock_logger.assert_called_with("Zendesk create ticket request failed with 401 '{'foo': 'bar'}'")


@pytest.mark.parametrize(
    "p1_arg, expected_tags, expected_priority, is_alarm_tag_expected",
    (
        (
            {},
            [
                "emergency_alerts_new_alarm",
                "emergency_alerts_send_slack_dev",
                "emergency_alerts_send_email_project",
            ],
            "normal",
            False,
        ),
        (
            {
                "p1": False,
            },
            [
                "emergency_alerts_new_alarm",
                "emergency_alerts_send_slack_dev",
                "emergency_alerts_send_email_project",
            ],
            "normal",
            False,
        ),
        (
            {
                "p1": True,
            },
            [
                "emergency_alerts_new_alarm",
                "emergency_alerts_send_slack_dev",
                "emergency_alerts_send_email_project",
                "emergency_alerts_send_pagerduty",
            ],
            "urgent",
            True,
        ),
    ),
)
def test_eas_support_ticket_request_data(p1_arg, expected_tags, expected_priority, is_alarm_tag_expected):
    eas_ticket_form = EASSupportTicket("subject", "message", "question", **p1_arg)

    assert eas_ticket_form.request_data == {
        "ticket": {
            "subject": "subject",
            "comment": {
                "body": "message",
                "public": True,
            },
            "group_id": EASSupportTicket.EAS_GROUP_ID,
            "organization_id": EASSupportTicket.EAS_ORG_ID,
            "ticket_form_id": EASSupportTicket.EAS_TICKET_FORM_ID,
            "priority": expected_priority,
            "tags": expected_tags,
            "type": "question",
            "custom_fields": [
                {"id": "9450265441308", "value": "emergency_alerts_ticket_type_non_technical"},
                {"id": "9450275731228", "value": []},
                {"id": "9450285728028", "value": None},
                {"id": "9450288116380", "value": None},
                {"id": "9450320852636", "value": None},
                {"id": "12554478022300", "value": "alarm" if is_alarm_tag_expected else "info"},
                {"id": "12712486813340", "value": "*Content*: message"},
                {"id": "12553900421276", "value": "*Requester*: None"},
            ],
        }
    }


def test_eas_support_ticket_request_data_with_message_hidden_from_requester():
    eas_ticket_form = EASSupportTicket("subject", "message", "problem", requester_sees_message_content=False)

    assert eas_ticket_form.request_data["ticket"]["comment"]["public"] is False


@pytest.mark.parametrize("name, zendesk_name", [("Name", "Name"), (None, "(no name supplied)")])
def test_eas_support_ticket_request_data_with_user_name_and_email(name, zendesk_name):
    eas_ticket_form = EASSupportTicket("subject", "message", "question", user_name=name, user_email="user@example.com")

    assert eas_ticket_form.request_data["ticket"]["requester"]["email"] == "user@example.com"
    assert eas_ticket_form.request_data["ticket"]["requester"]["name"] == zendesk_name


@pytest.mark.parametrize(
    "custom_fields, tech_ticket_tag, categories, org_id, org_type, service_id",
    [
        ({"technical_ticket": True}, "emergency_alerts_ticket_type_technical", [], None, None, None),
        ({"technical_ticket": False}, "emergency_alerts_ticket_type_non_technical", [], None, None, None),
        (
            {"ticket_categories": ["notify_bug"]},
            "emergency_alerts_ticket_type_non_technical",
            ["notify_bug"],
            None,
            None,
            None,
        ),
        (
            {"org_id": "1234", "org_type": "local"},
            "emergency_alerts_ticket_type_non_technical",
            [],
            "1234",
            "emergency_alerts_org_type_local",
            None,
        ),
        (
            {"service_id": "abcd", "org_type": "nhs"},
            "emergency_alerts_ticket_type_non_technical",
            [],
            None,
            "emergency_alerts_org_type_nhs",
            "abcd",
        ),
    ],
)
def test_eas_support_ticket_request_data_custom_fields(
    custom_fields,
    tech_ticket_tag,
    categories,
    org_id,
    org_type,
    service_id,
):
    eas_ticket_form = EASSupportTicket("subject", "message", "question", **custom_fields)

    assert eas_ticket_form.request_data["ticket"]["custom_fields"] == [
        {"id": "9450265441308", "value": tech_ticket_tag},
        {"id": "9450275731228", "value": categories},
        {"id": "9450285728028", "value": org_id},
        {"id": "9450288116380", "value": org_type},
        {"id": "9450320852636", "value": service_id},
        {"id": "12554478022300", "value": "info"},
        {"id": "12712486813340", "value": "*Content*: message"},
        {"id": "12553900421276", "value": "*Requester*: None"},
    ]


def test_eas_support_ticket_request_data_email_ccs():
    eas_ticket_form = EASSupportTicket("subject", "message", "question", email_ccs=["someone@example.com"])

    assert eas_ticket_form.request_data["ticket"]["email_ccs"] == [
        {"user_email": "someone@example.com", "action": "put"},
    ]


def test_eas_support_ticket_with_html_body():
    eas_ticket_form = EASSupportTicket("subject", "message", "task", message_as_html=True)

    assert eas_ticket_form.request_data == {
        "ticket": {
            "subject": "subject",
            "comment": {
                "html_body": "message",
                "public": True,
            },
            "group_id": EASSupportTicket.EAS_GROUP_ID,
            "organization_id": EASSupportTicket.EAS_ORG_ID,
            "ticket_form_id": EASSupportTicket.EAS_TICKET_FORM_ID,
            "priority": "normal",
            "tags": [
                "emergency_alerts_new_alarm",
                "emergency_alerts_send_slack_dev",
                "emergency_alerts_send_email_project",
            ],
            "type": "task",
            "custom_fields": [
                {"id": "9450265441308", "value": "emergency_alerts_ticket_type_non_technical"},
                {"id": "9450275731228", "value": []},
                {"id": "9450285728028", "value": None},
                {"id": "9450288116380", "value": None},
                {"id": "9450320852636", "value": None},
                {"id": "12554478022300", "value": "info"},
                {"id": "12712486813340", "value": "*Content*: message"},
                {"id": "12553900421276", "value": "*Requester*: None"},
            ],
        }
    }
