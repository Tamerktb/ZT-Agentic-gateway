"""
Demo Orchestrator

Runs the full Zero Trust Agentic AI Gateway demo sequence.
"""
import argparse
import subprocess
import sys
import time


def run_command(cmd: list[str], desc: str):
    print(f"\n{'='*60}")
    print(f"  {desc}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def demo_normal():
    steps = [
        (["docker", "compose", "exec", "demo-agents", "python", "shopping_agent.py"], "Normal Agent Flow"),
        (["docker", "compose", "exec", "demo-agents", "python", "sub_agent_spawner.py"], "Sub-Agent NHI Spawning"),
    ]
    for cmd, desc in steps:
        run_command(cmd, desc)
        time.sleep(1)


def demo_attacks():
    run_command(
        ["docker", "compose", "exec", "attack-simulator", "python", "attack_simulator.py"],
        "Attack Simulations (6 Zero Trust Controls)",
    )


def demo_full():
    demo_normal()
    print("\n")
    demo_attacks()
    print("\n")
    commands = [
        (["docker", "compose", "exec", "ai-gateway", "python", "-c", """
import httpx
r = httpx.get("http://localhost:8000/api/v1/admin/stats")
print(r.json())
"""], "Gateway Enforcement Stats"),
        (["docker", "compose", "exec", "audit-service", "python", "-c", """
import httpx
r = httpx.get("http://localhost:8004/api/v1/audit/stats")
print(r.json())
r2 = httpx.get("http://localhost:8004/api/v1/audit/chain/verify")
print(f"Chain integrity: {r2.json()}")
"""], "Audit Chain Verification"),
    ]
    for cmd, desc in commands:
        run_command(cmd, desc)
        time.sleep(0.5)


def main():
    parser = argparse.ArgumentParser(description="Zero Trust AI Gateway Demo")
    parser.add_argument("--scenario", choices=["normal", "attacks", "full"], default="full")
    args = parser.parse_args()

    if args.scenario == "normal":
        demo_normal()
    elif args.scenario == "attacks":
        demo_attacks()
    else:
        demo_full()


if __name__ == "__main__":
    main()
