"""
Stage 5 of the middleware pipeline: Audit Logging.
Records every agent action and decision in an immutable hash-chain audit log.
Each entry contains a SHA256 hash of the previous entry, making tampering detectable.
"""
import hashlib
import logging
import httpx
from src.config import settings

logger = logging.getLogger(__name__)


class AuditMiddleware:
    def __init__(self):
        self.audit_url = settings.audit_service_url

    async def log(self, entry: dict) -> bool:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.audit_url}/api/v1/audit/log",
                json=entry,
                timeout=5.0,
            )
            if resp.status_code != 200:
                logger.error(f"Audit log failed: {resp.text}")
                return False
            return True

    @staticmethod
    def compute_hash(entry: dict) -> str:
        raw = f"{entry.get('timestamp')}|{entry.get('agent_id')}|{entry.get('action_type')}|{entry.get('target')}|{entry.get('decision')}|{entry.get('prev_hash', '')}"
        return hashlib.sha256(raw.encode()).hexdigest()
