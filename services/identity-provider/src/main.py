"""
Identity Provider — manages Non-Human Identities (NHIs) for AI agents.
Handles agent registration, JWT issuance, and token verification.
Each agent gets a unique identity with a role and scoped policies.
"""
import os
import uuid
import logging
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

JWT_SECRET = os.environ.get("JWT_SECRET", "zt-lab-secret-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_TTL_MINUTES = 60

app = FastAPI(title="Identity Provider", version="1.0.0")

registered_agents: dict[str, dict] = {}

issue_log: list[dict] = []


class RegisterRequest(BaseModel):
    agent_id: str
    role: str
    policies: list[str] = []


class VerifyRequest(BaseModel):
    token: str


@app.post("/api/v1/nhi/register")
async def register_agent(req: RegisterRequest):
    if req.agent_id in registered_agents:
        raise HTTPException(status_code=409, detail="agent already registered")
    registered_agents[req.agent_id] = {
        "agent_id": req.agent_id,
        "role": req.role,
        "policies": req.policies,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "active": True,
    }
    logger.info(f"Registered NHI: {req.agent_id} (role: {req.role})")
    return registered_agents[req.agent_id]


@app.post("/api/v1/nhi/token")
async def issue_token(req: RegisterRequest):
    agent = registered_agents.get(req.agent_id)
    if not agent or not agent.get("active"):
        raise HTTPException(status_code=401, detail="agent not registered or inactive")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": req.agent_id,
        "role": agent["role"],
        "policies": agent["policies"],
        "iat": now,
        "exp": now + timedelta(minutes=JWT_TTL_MINUTES),
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    issue_log.append({"agent_id": req.agent_id, "issued_at": now.isoformat(), "jti": payload["jti"]})
    logger.info(f"Issued token for {req.agent_id} (expires in {JWT_TTL_MINUTES}m)")
    return {"token": token, "expires_in": JWT_TTL_MINUTES * 60, "agent_id": req.agent_id}


@app.post("/api/v1/nhi/verify")
async def verify_token(req: VerifyRequest):
    try:
        payload = jwt.decode(req.token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        agent = registered_agents.get(payload["sub"])
        if not agent or not agent.get("active"):
            raise HTTPException(status_code=401, detail="agent not active")
        logger.info(f"Token verified for {payload['sub']}")
        return {
            "allowed": True,
            "agent_id": payload["sub"],
            "role": payload.get("role"),
            "policies": payload.get("policies", []),
        }
    except jwt.ExpiredSignatureError:
        logger.warning("Token verification failed: expired")
        raise HTTPException(status_code=401, detail="token expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="invalid token")


@app.get("/api/v1/nhi/agents")
async def list_agents():
    return {"agents": list(registered_agents.values())}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "identity-provider", "agents_registered": len(registered_agents)}


@app.get("/")
async def root():
    return {"service": "Identity Provider", "version": "1.0.0", "status": "running"}
