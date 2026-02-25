class QueueNames:
    PERIODIC = "periodic-tasks"
    BROADCASTS = "broadcast-tasks"
    GOVUK_ALERTS = "govuk-alerts"
    HIGH_PRIORITY = "high-priority-tasks"


class TaskNames:
    PUBLISH_GOVUK_ALERTS = "publish-govuk-alerts"
    SEND_BROADCAST_EVENT = "send-broadcast-event"
    SEND_BROADCAST_PROVIDER_MESSAGE = "send-broadcast-provider-message"
    REQUEST_LOG_INGEST = "request-log-ingest"
    TRIGGER_LINK_TEST = "trigger-link-test"  # (singular - not to be confused with the plural that's scheduled)
    TRIGGER_LINK_TEST_PRIMARY_TO_A = "trigger-link-test-primary-to-A"
    TRIGGER_LINK_TEST_PRIMARY_TO_B = "trigger-link-test-primary-to-B"
    TRIGGER_LINK_TEST_SECONDARY_TO_A = "trigger-link-test-secondary-to-A"
    TRIGGER_LINK_TEST_SECONDARY_TO_B = "trigger-link-test-secondary-to-B"

    # Scheduled
    TRIGGER_GOVUK_HEALTHCHECK = "trigger-govuk-alerts-healthcheck"
    RUN_HEALTH_CHECK = "run-health-check"
    DELETE_VERIFY_CODES = "delete-verify-codes"
    DELETE_INVITATIONS = "delete-invitations"
    TRIGGER_LINK_TESTS = "trigger-link-tests"
    AUTO_EXPIRE_BROADCAST_MESSAGES = "auto-expire-broadcast-messages"
    REMOVE_YESTERDAYS_PLANNED_TESTS_ON_GOVUK_ALERTS = "remove-yesterdays-planned-tests-on-govuk-alerts"
    DELETE_OLD_RECORDS_FROM_EVENTS_TABLE = "delete-old-records-from-events-table"
    VALIDATE_FUNCTIONAL_TEST_ACCOUNT_EMAILS = "validate-functional-test-account-emails"
    QUEUE_AFTER_ALERT_ACTIVITIES = "queue-after-alert-activities"
