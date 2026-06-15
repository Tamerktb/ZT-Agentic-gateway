package tool_policy

tool_controls = {
    "purchase_item": {
        "require_mfa": false,
        "require_human_approval": false,
        "max_amount": 500,
        "allowed_hours_only": false,
        "restrict_actions": ["call_tool"],
    },
    "check_inventory": {
        "require_mfa": false,
        "require_human_approval": false,
        "max_amount": 0,
        "restrict_actions": ["call_tool"],
    },
    "refund_order": {
        "require_mfa": true,
        "require_human_approval": true,
        "max_amount": 200,
        "restrict_actions": ["call_tool"],
    },
    "read_dataset": {
        "require_mfa": false,
        "require_human_approval": false,
        "max_amount": 0,
        "restrict_actions": ["call_tool", "read_data"],
    },
    "spawn_agent": {
        "require_mfa": true,
        "require_human_approval": true,
        "max_amount": 0,
        "restrict_actions": ["call_tool"],
    },
    "send_email": {
        "require_mfa": false,
        "require_human_approval": false,
        "max_amount": 0,
        "restrict_actions": ["call_tool"],
    },
    "delete_user": {
        "require_mfa": true,
        "require_human_approval": true,
        "max_amount": 0,
        "restrict_actions": [],
    },
}
