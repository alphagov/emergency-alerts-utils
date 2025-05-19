from datetime import timedelta

# Tasks which require another platform admin to approve before being actioned
ADMIN_INVITE_USER = "invite_user"
ADMIN_EDIT_PERMISSIONS = "edit_permissions"  # Only if adding permissions, removal does not need approval
ADMIN_CREATE_API_KEY = "create_api_key"
ADMIN_ELEVATE_USER = "elevate_platform_admin"  # To elevate the creator temporarily

ADMIN_ACTION_LIST = [
    ADMIN_INVITE_USER,
    ADMIN_EDIT_PERMISSIONS,
    ADMIN_CREATE_API_KEY,
    ADMIN_ELEVATE_USER,
]

ADMIN_STATUS_PENDING = "pending"
ADMIN_STATUS_APPROVED = "approved"
ADMIN_STATUS_REJECTED = "rejected"
ADMIN_STATUS_INVALIDATED = "invalidated"

ADMIN_STATUS_LIST = [
    ADMIN_STATUS_PENDING,
    ADMIN_STATUS_APPROVED,
    ADMIN_STATUS_REJECTED,
    ADMIN_STATUS_INVALIDATED,
]

# Permissions which require approval from an additional admin before being added
ADMIN_SENSITIVE_PERMISSIONS = ["create_broadcasts", "approve_broadcasts"]

# How long elevation requests (AdminAction) can exist before automatically invalidating
ADMIN_ELEVATION_ACTION_TIMEOUT = timedelta(hours=2)
# How long an approved elevation can remain unredeemed for before the next login doesn't grant platform admin
ADMIN_ELEVATION_REDEMPTION_TIMEOUT = timedelta(hours=24)

ADMIN_ZENDESK_TICKET_TITLE_PREFIX = "Admin Activity Out of Hours"
# Treat outside of 8am - 6pm as outside office hours:
ADMIN_ZENDESK_OFFICE_HOURS_START = "8"
ADMIN_ZENDESK_OFFICE_HOURS_END = "6"

# What each event should be as a priority in ZenDesk when it occurs out of hours:
ADMIN_ZENDESK_PRIORITY_REQUEST = "low"
ADMIN_ZENDESK_PRIORITY_APPROVE = "normal"
ADMIN_ZENDESK_PRIORITY_ELEVATED = "urgent"
