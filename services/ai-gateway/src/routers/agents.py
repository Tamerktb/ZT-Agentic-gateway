import uuid
import hashlib
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Header
from src.models.schemas import AgentActionRequest, AgentActionResponse
from src.middleware import (
    AuthMiddleware,
    PolicyMiddleware,
    RateLimitMiddleware,
    PromptInspectionMiddleware,
    AuditMiddleware,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])

auth_mw = AuthMiddleware()
policy_mw = PolicyMiddleware()
rate_limit_mw = RateLimitMiddleware()
inspect_mw = PromptInspectionMiddleware()
audit_mw = AuditMiddleware()


@router.post("/action", response_model=AgentActionResponse)
async def execute_action(req: AgentActionRequest, authorization: str = Header(...)):
    trace_id = str(uuid.uuid4())
    decisions = []
    allowed = True
    final_reason = None

    token = authorization.replace("Bearer ", "")

    ts = datetime.now(timezone.utc).isoformat()

    # Stage 1: Authenticate
    auth_result = await auth_mw.verify(token)
    decisions.append(auth_result)
    if not auth_result.get("allowed"):
        await _log_audit(trace_id, req, "DENIED-auth", ts, decisions)
        raise HTTPException(status_code=401, detail=auth_result.get("reason"))

    # Stage 2: Policy check
    agent_role = auth_result.get("agent", {}).get("role", "")
    policy_result = await policy_mw.evaluate(req.agent_id, req.action_type.value, req.target, req.payload, role=agent_role)
    decisions.append(policy_result)
    if not policy_result.get("allowed"):
        await _log_audit(trace_id, req, "DENIED-policy", ts, decisions)
        raise HTTPException(status_code=403, detail=policy_result.get("reason"))

    # Stage 3: Rate limit
    rate_result = await rate_limit_mw.check(req.agent_id, req.action_type.value, req.payload)
    decisions.append(rate_result)
    if not rate_result.get("allowed"):
        await _log_audit(trace_id, req, "DENIED-rate_limit", ts, decisions)
        raise HTTPException(status_code=429, detail=rate_result.get("reason"))

    # Stage 4: Prompt inspection
    inspect_result = await inspect_mw.inspect(req.agent_id, req.action_type.value, req.target, req.payload)
    decisions.append(inspect_result)
    if not inspect_result.get("allowed"):
        await _log_audit(trace_id, req, "DENIED-inspection", ts, decisions)
        raise HTTPException(status_code=400, detail=inspect_result.get("reason"))

    # Stage 5: All checks passed - get dynamic credentials and execute
    logger.info(f"All checks passed for {req.agent_id} ({trace_id}). Action ALLOWED.")
    await _log_audit(trace_id, req, "ALLOWED", ts, decisions)

    return AgentActionResponse(
        status="allowed",
        result={
            "message": f"Action {req.action_type.value} on {req.target} executed successfully",
            "trace_id": trace_id,
        },
        trace_id=trace_id,
    )


async def _log_audit(trace_id: str, req: AgentActionRequest, decision: str, timestamp: str, decisions: list):
    input_hash = hashlib.sha256(str(req.payload).encode()).hexdigest()
    entry = {
        "trace_id": trace_id,
        "agent_id": req.agent_id,
        "action_type": req.action_type.value,
        "target": req.target,
        "input_hash": input_hash,
        "decision": decision,
        "timestamp": timestamp,
        "decisions": decisions,
    }
    await audit_mw.log(entry)
