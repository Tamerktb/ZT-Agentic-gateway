package agent_policy

role_tools = {
    "shopping_agent": [
        "purchase_item",
        "check_inventory",
        "refund_order",
        "get_order_status",
    ],
    "data_processor": [
        "read_dataset",
        "transform_data",
        "generate_report",
    ],
    "email_agent": [
        "send_email",
        "read_inbox",
    ],
    "orchestrator": [
        "spawn_agent",
        "monitor_agents",
        "kill_agent",
    ],
    "unknown": [],
}
