# Tasks which require another platform admin to approve before being actioned
ADMIN_INVITE_USER = "invite_user"
ADMIN_EDIT_PERMISSIONS = "edit_permissions"  # Only if adding permissions, removal does not need approval
ADMIN_CREATE_API_KEY = "create_api_key"

ADMIN_ACTION_LIST = [
    ADMIN_INVITE_USER,
    ADMIN_EDIT_PERMISSIONS,
    ADMIN_CREATE_API_KEY,
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
