"""
Shopping Agent Demo

Demonstrates a legitimate agent with valid NHI credentials
going through the Zero Trust pipeline successfully.
"""
import os
import sys
import time
import httpx

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000")
IDP_URL = os.environ.get("IDP_URL", "http://identity-provider:8001")


def register_agent():
    resp = httpx.post(
        f"{IDP_URL}/api/v1/nhi/register",
        json={"agent_id": "shopping-agent", "role": "shopping_agent", "policies": ["purchase_item", "check_inventory"]},
    )
    print(f"[REGISTER] Status: {resp.status_code} - {resp.json()}")
    return resp.status_code == 200


def get_token():
    resp = httpx.post(
        f"{IDP_URL}/api/v1/nhi/token",
        json={"agent_id": "shopping-agent", "role": "shopping_agent", "policies": ["purchase_item", "check_inventory"]},
    )
    data = resp.json()
    print(f"[TOKEN] Status: {resp.status_code} - token={data.get('token', '')[:40]}...")
    return data.get("token")


def call_gateway(token: str, action_type: str, target: str, payload: dict):
    resp = httpx.post(
        f"{GATEWAY_URL}/api/v1/agent/action",
        json={
            "agent_id": "shopping-agent",
            "action_type": action_type,
            "target": target,
            "payload": payload,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp


def main():
    print("=" * 60)
    print("ZERO TRUST AI GATEWAY — SHOPPING AGENT DEMO")
    print("=" * 60)
    print()

    print(">>> Step 1: Register NHI (Non-Human Identity)")
    register_agent()
    print()

    print(">>> Step 2: Get JWT Token")
    token = get_token()
    if not token:
        print("FAILED: Could not get token")
        sys.exit(1)
    print()

    print(">>> Step 3: Execute Legitimate Actions")
    print("-" * 40)

    scenarios = [
        ("call_tool", "check_inventory", {"product_id": "PROD-001"}, "Check inventory"),
        ("call_tool", "purchase_item", {"product_id": "PROD-001", "amount": 49.99, "quantity": 1}, "Purchase under $500"),
    ]

    for action_type, target, payload, desc in scenarios:
        print(f"\n  [{desc}]")
        print(f"    action: {action_type} on {target}")
        print(f"    payload: {payload}")
        resp = call_gateway(token, action_type, target, payload)
        print(f"    Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"    Result: ALLOWED ✓")
        else:
            print(f"    Result: BLOCKED ✗ - {resp.text}")
        time.sleep(0.5)

    print()
    print("=" * 60)
    print("DEMO COMPLETE — Legitimate agent flow succeeded")
    print("=" * 60)


if __name__ == "__main__":
    main()
