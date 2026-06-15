from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class ActionType(str, Enum):
    call_tool = "call_tool"
    call_api = "call_api"
    read_data = "read_data"
    write_data = "write_data"
    spawn_agent = "spawn_agent"


class AgentActionRequest(BaseModel):
    agent_id: str
    action_type: ActionType
    target: str
    payload: dict = Field(default_factory=dict)
    context: Optional[dict] = None


class AgentActionResponse(BaseModel):
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None
    trace_id: str


class EnforcementDecision(BaseModel):
    allowed: bool
    reason: str
    component: str


class AuditEntry(BaseModel):
    trace_id: str
    agent_id: str
    action_type: str
    target: str
    input_hash: str
    decision: str
    timestamp: str
    prev_hash: str
    hash: str
