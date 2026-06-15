import logging
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

kill_switch_state: dict[str, bool] = {}
stats = {
    "total_actions": 0,
    "allowed": 0,
    "denied_auth": 0,
    "denied_policy": 0,
    "denied_rate_limit": 0,
    "denied_inspection": 0,
}


@router.post("/kill-switch/{agent_id}")
async def activate_kill_switch(agent_id: str):
    kill_switch_state[agent_id] = True
    logger.warning(f"KILL SWITCH ACTIVATED for agent: {agent_id}")
    return {"status": "killed", "agent_id": agent_id}


@router.post("/kill-switch/{agent_id}/release")
async def release_kill_switch(agent_id: str):
    kill_switch_state.pop(agent_id, None)
    logger.info(f"Kill switch released for agent: {agent_id}")
    return {"status": "released", "agent_id": agent_id}


@router.get("/kill-switch/{agent_id}")
async def check_kill_switch(agent_id: str):
    return {"agent_id": agent_id, "killed": kill_switch_state.get(agent_id, False)}


@router.get("/stats")
async def get_stats():
    return stats


def record_decision(decision: str):
    stats["total_actions"] += 1
    key_map = {
        "ALLOWED": "allowed",
        "DENIED-auth": "denied_auth",
        "DENIED-policy": "denied_policy",
        "DENIED-rate_limit": "denied_rate_limit",
        "DENIED-inspection": "denied_inspection",
    }
    key = key_map.get(decision, "denied_auth")
    stats[key] += 1
