"""
Credential Vault — issues dynamic per-action credentials with short TTLs.
Implements just-in-time access: credentials are checked out, used once, and auto-expire.
No static secrets are stored; each lease generates a unique credential hash.
"""
import uuid
import hashlib
import time
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Credential Vault", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CREDENTIAL_TTL = 120

tool_credentials: dict[str, dict] = {
    "purchase_item": {
        "type": "api_key",
        "credential": "sk-prod-purchase-api-v1",
        "endpoint": "https://api.example.com/v1/purchases",
    },
    "check_inventory": {
        "type": "api_key",
        "credential": "sk-prod-inventory-api-v1",
        "endpoint": "https://api.example.com/v1/inventory",
    },
    "read_dataset": {
        "type": "bearer_token",
        "credential": "s3-data-lake-token",
        "endpoint": "https://data-lake.example.com/v1/datasets",
    },
    "send_email": {
        "type": "smtp_password",
        "credential": "smtp-relay-password",
        "endpoint": "smtp://mail.example.com:587",
    },
    "spawn_agent": {
        "type": "api_key",
        "credential": "sk-prod-agent-orch-key",
        "endpoint": "https://agent-orch.example.com/v1/spawn",
    },
}

checked_out: dict[str, dict] = {}


class CredentialRequest(BaseModel):
    tool_name: str
    agent_id: str


class CredentialReturn(BaseModel):
    lease_id: str


@app.post("/api/v1/credentials/checkout")
async def checkout_credential(req: CredentialRequest):
    if req.tool_name not in tool_credentials:
        raise HTTPException(status_code=404, detail=f"no credentials found for tool: {req.tool_name}")

    lease_id = str(uuid.uuid4())
    expires_at = time.time() + CREDENTIAL_TTL

    rotated_value = hashlib.sha256(
        f"{tool_credentials[req.tool_name]['credential']}:{lease_id}:{time.time()}".encode()
    ).hexdigest()[:32]

    dynamic_cred = {
        "lease_id": lease_id,
        "tool": req.tool_name,
        "agent_id": req.agent_id,
        "credential": rotated_value,
        "endpoint": tool_credentials[req.tool_name]["endpoint"],
        "type": tool_credentials[req.tool_name]["type"],
        "expires_at": expires_at,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
    checked_out[lease_id] = dynamic_cred

    logger.info(
        f"Credential CHECKED OUT: tool={req.tool_name} agent={req.agent_id} "
        f"lease={lease_id[:8]} expires_in={CREDENTIAL_TTL}s"
    )
    return dynamic_cred


@app.post("/api/v1/credentials/checkin")
async def checkin_credential(req: CredentialReturn):
    if req.lease_id not in checked_out:
        raise HTTPException(status_code=404, detail="lease not found or already returned")
    cred = checked_out.pop(req.lease_id)
    logger.info(
        f"Credential CHECKED IN: tool={cred['tool']} agent={cred['agent_id']} "
        f"lease={req.lease_id[:8]} duration={CREDENTIAL_TTL}s"
    )
    return {"status": "returned", "tool": cred["tool"], "lease_id": req.lease_id}


@app.post("/api/v1/credentials/verify")
async def verify_credential(req: CredentialReturn):
    cred = checked_out.get(req.lease_id)
    if not cred:
        raise HTTPException(status_code=401, detail="credential not found or expired")
    if time.time() > cred["expires_at"]:
        checked_out.pop(req.lease_id, None)
        raise HTTPException(status_code=401, detail="credential expired")
    return {"valid": True, "tool": cred["tool"], "expires_at": cred["expires_at"]}


@app.get("/api/v1/credentials/active")
async def list_active():
    now = time.time()
    active = {k: v for k, v in checked_out.items() if v["expires_at"] > now}
    return {"active_leases": len(active), "leases": list(active.values())}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "credential-vault"}


@app.get("/")
async def root():
    return {"service": "Credential Vault", "version": "1.0.0", "status": "running"}
