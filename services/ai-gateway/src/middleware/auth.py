"""
Stage 1 of the middleware pipeline: Authentication.
Verifies that the agent's JWT token was issued by the Identity Provider.
Rejects invalid, expired, or forged tokens with HTTP 401.
"""
import logging
import httpx
from src.config import settings

logger = logging.getLogger(__name__)


class AuthMiddleware:
    def __init__(self):
        self.idp_url = settings.identity_provider_url

    async def verify(self, token: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.idp_url}/api/v1/nhi/verify",
                json={"token": token},
                timeout=5.0,
            )
            if resp.status_code != 200:
                logger.warning(f"Auth failed: {resp.text}")
                return {"allowed": False, "reason": resp.json().get("detail", "authentication failed")}
            data = resp.json()
            logger.info(f"Agent authenticated: {data.get('agent_id')}")
            return {"allowed": True, "agent": data}
