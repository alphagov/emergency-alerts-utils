import pytest

from emergency_alerts_utils.clients.slack.slack_client import (
    SlackClient,
    SlackError,
    SlackMessage,
)


@pytest.fixture(scope="function")
def slack_client(app):
    return SlackClient()


def test_slack_client_send_message_to_slack(slack_client, app, mocker, rmock):
    webhook_url = "https://fake-url"
    subject = "Something has gone wrong"
    message_type = "info"
    markdown_sections = ["Description of what has gone wrong"]

    rmock.request(
        "POST",
        webhook_url,
        status_code=200,
        json={
            "attachments": [
                {
                    "color": "#ff0000",
                    "blocks": [
                        {"type": "header", "text": {"type": "plain_text", "text": subject}},
                        {"type": "divider"},
                        {"type": "section", "text": {"type": "mrkdwn", "text": markdown_sections[0]}},
                    ],
                }
            ]
        },
    )

    mock_logger = mocker.patch.object(app.logger, "info")

    message = SlackMessage(
        webhook_url=webhook_url, subject=subject, message_type=message_type, markdown_sections=markdown_sections
    )
    slack_client.send_message_to_slack(message)

    assert rmock.last_request.json() == message.request_data
    mock_logger.assert_called_once_with("Slack message sent successfully.")


def test_slack_client_send_message_to_slack_error(slack_client, app, mocker, rmock):
    webhook_url = "https://fake-url"
    subject = "Something has gone wrong"
    message_type = "info"
    markdown_sections = ["Description of what has gone wrong"]

    rmock.request("POST", "fake-url", status_code=401, json={"foo": "bar"})

    mock_logger = mocker.patch.object(app.logger, "error")

    message = SlackMessage(
        webhook_url=webhook_url, subject=subject, message_type=message_type, markdown_sections=markdown_sections
    )

    with pytest.raises(SlackError):
        slack_client.send_message_to_slack(message)

    mock_logger.assert_called_with("Slack message creation request failed with 401")
