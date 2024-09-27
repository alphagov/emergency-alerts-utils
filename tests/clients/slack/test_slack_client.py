import pytest

from emergency_alerts_utils.clients.slack.slack_client import (
    SlackClient,
    SlackError,
    SlackMessage,
)


@pytest.fixture(scope="function")
def zendesk_client(app):
    return SlackClient()


def test_slack_client_send_message_to_slack(slack_client, app, mocker, rmock):
    rmock.request(
        "POST",
        "fake-url",
        status_code=200,
        json={
            "attachments": [
                {
                    "color": "#ff0000",
                    "blocks": [
                        {"type": "header", "text": {"type": "plain_text", "text": "Something has gone wrong"}},
                        {"type": "divider"},
                        {"type": "section", "text": {"type": "mrkdwn", "text": "Description of what has gone wrong"}},
                    ],
                }
            ]
        },
    )

    mock_logger = mocker.patch.object(app.logger, "info")

    message = SlackMessage()
    slack_client.send_message_to_slack(message)

    assert rmock.last_request.json() == message.request_data
    mock_logger.assert_called_once_with("Slack message sent successfully.")


def test_zendesk_client_send_ticket_to_zendesk_error(zendesk_client, app, mocker, rmock):
    rmock.request("POST", "fake-url", status_code=401, json={"foo": "bar"})

    mock_logger = mocker.patch.object(app.logger, "error")

    ticket = SlackMessage({"something": "anything"})

    with pytest.raises(SlackError):
        zendesk_client.send_ticket_to_zendesk(ticket)

    mock_logger.assert_called_with("Slack message creation request failed with 401")
