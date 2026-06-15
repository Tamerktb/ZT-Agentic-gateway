"""
Stage 2 of the middleware pipeline: Policy Enforcement.
Checks if the agent's role has permission to use the requested tool.
Returns 403 if the action is outside the agent's allowed scope.
"""
import logging
import httpx
from src.config import settings

logger = logging.getLogger(__name__)


class PolicyMiddleware:
    def __init__(self):
        self.policy_url = settings.policy_engine_url

    async def evaluate(self, agent_id: str, action_type: str, target: str, payload: dict, role: str = "") -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.policy_url}/api/v1/policy/evaluate",
                json={
                    "agent_id": agent_id,
                    "action_type": action_type,
                    "target": target,
                    "payload": payload,
                    "role": role,
                },
                timeout=5.0,
            )
            if resp.status_code != 200:
                logger.error(f"Policy engine error: {resp.text}")
                return {"allowed": False, "reason": "policy engine unavailable", "component": "policy"}
            decision = resp.json()
            if not decision.get("allowed", False):
                logger.warning(f"Policy DENIED: {agent_id} -> {action_type} on {target}: {decision.get('reason')}")
            else:
                logger.info(f"Policy ALLOWED: {agent_id} -> {action_type} on {target}")
            return decision
