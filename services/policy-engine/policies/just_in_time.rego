package just_in_time

jit_policies = {
    "shopping-agent": {
        "max_daily_actions": 100,
        "max_daily_spend": 5000.00,
        "session_ttl_minutes": 30,
        "allow_outside_business_hours": false,
    },
    "data-processor": {
        "max_daily_actions": 1000,
        "max_daily_spend": 0,
        "session_ttl_minutes": 120,
        "allow_outside_business_hours": true,
    },
    "email-agent": {
        "max_daily_actions": 200,
        "max_daily_spend": 0,
        "session_ttl_minutes": 60,
        "allow_outside_business_hours": true,
    },
}
