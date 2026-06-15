"""
Sub-Agent Creator Demo

Demonstrates how an orchestrator agent spawns sub-agents,
each getting their own unique NHI with limited privileges.
"""
import os
import httpx

IDP_URL = os.environ.get("IDP_URL", "http://identity-provider:8001")


def main():
    print("=" * 60)
    print("SUB-AGENT SPAWNER DEMO")
    print("Each sub-agent gets a unique NHI with least privilege")
    print("=" * 60)
    print()

    # Register orchestrator
    print(">>> Register orchestrator agent")
    r = httpx.post(
        f"{IDP_URL}/api/v1/nhi/register",
        json={"agent_id": "orchestrator-1", "role": "orchestrator", "policies": ["spawn_agent", "monitor_agents"]},
    )
    print(f"  {r.json()}")
    print()

    # Spawn sub-agents with unique NHIs
    sub_agents = [
        ("sub-inventory-1", "shopping_agent", ["check_inventory"]),
        ("sub-inventory-2", "shopping_agent", ["check_inventory"]),
        ("sub-email-1", "email_agent", ["send_email"]),
    ]
    for agent_id, role, policies in sub_agents:
        r = httpx.post(
            f"{IDP_URL}/api/v1/nhi/register",
            json={"agent_id": agent_id, "role": role, "policies": policies},
        )
        token_r = httpx.post(
            f"{IDP_URL}/api/v1/nhi/token",
            json={"agent_id": agent_id, "role": role, "policies": policies},
        )
        data = token_r.json()
        print(f"  Spawned: {agent_id:<20} role={role:<16} token={data.get('token', '')[:30]}...")

    print()
    print("Each sub-agent has:")
    print("  - Unique NHI (separate identity)")
    print("  - Least-privilege role (only their needed tools)")
    print("  - Scoped policy (can't access other tools)")
    print()


if __name__ == "__main__":
    main()
