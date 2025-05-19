from typing import Optional

import requests
from flask import current_app

from emergency_alerts_utils.admin_action import ADMIN_ZENDESK_TICKET_TITLE_PREFIX


class ZendeskError(Exception):
    def __init__(self, response):
        self.response = response


class ZendeskClient:
    ZENDESK_TICKET_URL = "https://govuk.zendesk.com/api/v2/tickets.json"
    ZENDESK_SEARCH_TICKETS_URL = "https://govuk.zendesk.com/api/v2/search.json"
    ZENDESK_TICKET_ID_URL_PREFIX = "https://govuk.zendesk.com/api/v2/tickets/"  # + <id>

    def __init__(self):
        self.api_key = None

    def init_app(self, app, *args, **kwargs):
        self.api_key = app.config.get("ZENDESK_API_KEY")

    def headers(self):
        return {"Accept": "application/json", "Authorization": f"Basic {self.api_key}"}

    def send_ticket_to_zendesk(self, ticket):
        response = requests.post(self.ZENDESK_TICKET_URL, json=ticket.request_data, headers=self.headers())

        if response.status_code != 201:
            current_app.logger.error(
                f"Zendesk create ticket request failed with {response.status_code} '{response.json()}'"
            )
            raise ZendeskError(response)

        ticket_id = response.json()["ticket"]["id"]

        current_app.logger.info(f"Zendesk create ticket {ticket_id} succeeded")

    def get_open_admin_zendesk_ticket_id_for_email(self, email) -> Optional[int]:
        """
        Get a ticket ID if there's an open ticket referring to admin activity out of hours.
        Note that the email is expected to always be concerning the invidivual *becoming* an admin, not any approver.
        """
        params = {"query": f"type:ticket status:open {ADMIN_ZENDESK_TICKET_TITLE_PREFIX} requester:{email}"}
        response = requests.get(self.ZENDESK_SEARCH_TICKETS_URL, params=params, headers=self.headers())
        json = response.json()

        if json["count"] == 0:
            return None

        return json["results"][0]["id"]

    def update_ticket_priority(self, ticket_id: int, priority: str):
        if priority not in [
            EASSupportTicket.PRIORITY_LOW,
            EASSupportTicket.PRIORITY_NORMAL,
            EASSupportTicket.PRIORITY_HIGH,
            EASSupportTicket.PRIORITY_URGENT,
        ]:
            raise ZendeskError(f"Priority {priority} is unknown")

        response = requests.put(
            self.ZENDESK_TICKET_ID_URL_PREFIX + str(ticket_id), json={"priority": priority}, headers=self.headers()
        )
        return response


class EASSupportTicket:
    PRIORITY_URGENT = "urgent"
    PRIORITY_HIGH = "high"
    PRIORITY_NORMAL = "normal"
    PRIORITY_LOW = "low"

    TARGET_TAGS = {
        "SLACK_DEV": "emergency_alerts_send_slack_dev",
        "SLACK_TEST": "emergency_alerts_send_slack_test",
        "SLACK_SUPPORT": "emergency_alerts_send_slack_support",
        "SLACK_PIPELINES": "emergency_alerts_send_slack_pipelines",
        "EMAIL_TEST": "emergency_alerts_send_email_test",
        "EMAIL_GROUP_MAILBOX": "emergency_alerts_send_email_project",
        "EMAIL_SITCEN": "emergency_alerts_send_email_sitcen",
        "PAGERDUTY": "emergency_alerts_send_pagerduty",
    }

    # All tickets using visual formatting to Slack/Email recipients must have this tag
    BASE_TAGS = ["emergency_alerts_new_alarm"]
    TAGS_P2 = BASE_TAGS + [TARGET_TAGS["SLACK_DEV"], TARGET_TAGS["EMAIL_GROUP_MAILBOX"]]
    TAGS_P1 = TAGS_P2 + [TARGET_TAGS["PAGERDUTY"]]

    TYPE_PROBLEM = "problem"
    TYPE_INCIDENT = "incident"
    TYPE_QUESTION = "question"
    TYPE_TASK = "task"

    # Group: 3rd Line--Emergency Alerts Support
    EAS_GROUP_ID = 21842358
    # Organization: GDS
    EAS_ORG_ID = 21891972
    EAS_TICKET_FORM_ID = 9450316961820

    def __init__(
        self,
        subject,
        message,
        ticket_type,
        p1=False,
        user_name=None,
        user_email=None,
        requester_sees_message_content=True,
        technical_ticket=False,
        ticket_categories=None,
        org_id=None,
        org_type=None,
        service_id=None,
        email_ccs=None,
        message_as_html=False,
    ):
        self.subject = subject
        self.message = message
        self.ticket_type = ticket_type
        self.p1 = p1
        self.user_name = user_name
        self.user_email = user_email
        self.requester_sees_message_content = requester_sees_message_content
        self.technical_ticket = technical_ticket
        self.ticket_categories = ticket_categories or []
        self.org_id = org_id
        self.org_type = org_type
        self.service_id = service_id
        self.email_ccs = email_ccs
        self.message_as_html = message_as_html

    @property
    def request_data(self):
        data = {
            "ticket": {
                "subject": self.subject,
                "comment": {
                    ("html_body" if self.message_as_html else "body"): self.message,
                    "public": self.requester_sees_message_content,
                },
                "group_id": self.EAS_GROUP_ID,
                "organization_id": self.EAS_ORG_ID,
                "ticket_form_id": self.EAS_TICKET_FORM_ID,
                "priority": self.PRIORITY_URGENT if self.p1 else self.PRIORITY_NORMAL,
                "tags": self.TAGS_P1 if self.p1 else self.TAGS_P2,
                "type": self.ticket_type,
                "custom_fields": self._get_custom_fields(),
            }
        }

        if self.email_ccs:
            data["ticket"]["email_ccs"] = [{"user_email": email, "action": "put"} for email in self.email_ccs]

        if self.user_email:
            data["ticket"]["requester"] = {"email": self.user_email, "name": self.user_name or "(no name supplied)"}

        return data

    def _get_custom_fields(self):
        technical_ticket_tag = f'emergency_alerts_ticket_type_{"" if self.technical_ticket else "non_"}technical'
        org_type_tag = f"emergency_alerts_org_type_{self.org_type}" if self.org_type else None
        ticket_status_tag = "alarm" if self.p1 else "info"

        requester = self.user_name or "(no name supplied)"

        return [
            {"id": "9450265441308", "value": technical_ticket_tag},  # Ticket type field
            {"id": "9450275731228", "value": self.ticket_categories},  # Ticket category field
            {"id": "9450285728028", "value": self.org_id},  # Organisation ID field
            {"id": "9450288116380", "value": org_type_tag},  # Organisation type field
            {"id": "9450320852636", "value": self.service_id},  # Service ID field
            {"id": "12811397846172", "value": ticket_status_tag},  # Ticket colour/status field
            {"id": "12811367206428", "value": f"*Content*: {self.message}"},  # Ticket content visual display
            {"id": "12811389347356", "value": f"*Requester*: {requester}"},  # Ticket requester visual display
        ]
