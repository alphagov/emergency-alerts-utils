import requests
from flask import current_app


class SlackError(Exception):
    def __init__(self, response):
        self.response = response


class SlackClient:

    def __init__(self):
        self.webhook_url = None

    def send_message_to_slack(self, message):
        self.message = message.request_data
        headers = {"Accept": "application/json"}
        response = requests.post(message.webhook_url, json=self.message, headers=headers)

        if response.status_code != 200:
            current_app.logger.error(f"Slack message creation request failed with {response.status_code}")
            raise SlackError(response)

        current_app.logger.info("Slack message sent to the provided webhook URL.")


class SlackMessage:

    message_status_colours = {"success": "#02b101", "error": "#e82b2a", "info": "#f5ca00", "general": "#68737d"}

    def __init__(self, webhook_url, subject, message_type, markdown_sections):
        self.webhook_url = webhook_url
        self.subject = subject
        self.message_type = message_type
        self.markdown_sections = markdown_sections

    @property
    def message_colour(self):
        return self.message_status_colours[self.message_type]

    @property
    def request_data(self):
        return {
            "attachments": [
                {
                    "color": self.message_colour,
                    "blocks": [
                        {"type": "header", "text": {"type": "plain_text", "text": self.subject}},
                        {"type": "divider"},
                    ]
                    + [
                        {"type": "section", "text": {"type": "mrkdwn", "text": markdown_section}}
                        for markdown_section in self.markdown_sections
                    ],
                }
            ]
        }
