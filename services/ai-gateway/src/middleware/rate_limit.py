"""
Stage 3 of the middleware pipeline: Rate Limiting.
Prevents runaway agents from exceeding action frequency or budget caps.
Returns 429 if the agent exceeds 10 actions/minute or $1000/hr spend.
"""
import time
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    def __init__(self):
        self.max_actions_per_minute = 10
        self.max_budget_per_hour = 1000.0
        self.action_counts: dict = defaultdict(list)
        self.budget_usage: dict = defaultdict(float)

    async def check(self, agent_id: str, action_type: str, payload: dict) -> dict:
        now = time.time()

        action_times = self.action_counts[agent_id]
        self.action_counts[agent_id] = [t for t in action_times if now - t < 60]
        if len(self.action_counts[agent_id]) >= self.max_actions_per_minute:
            logger.warning(f"Rate limit exceeded for {agent_id}: {len(self.action_counts[agent_id])} actions in 60s")
            return {"allowed": False, "reason": f"rate limit: max {self.max_actions_per_minute} actions/min", "component": "rate_limit"}

        cost = abs(payload.get("amount", 0)) if "amount" in payload else 1
        if self.budget_usage[agent_id] + cost > self.max_budget_per_hour:
            logger.warning(f"Budget limit exceeded for {agent_id}: ${self.budget_usage[agent_id]:.2f} + ${cost:.2f}")
            return {"allowed": False, "reason": f"budget limit: ${self.max_budget_per_hour:.2f}/hr exceeded", "component": "rate_limit"}

        self.action_counts[agent_id].append(now)
        self.budget_usage[agent_id] += cost
        return {"allowed": True, "cost": cost}
