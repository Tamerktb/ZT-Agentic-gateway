"""
Audit Service — maintains an immutable hash-chain log of all agent actions.
Each entry contains a SHA256 hash of the previous entry (blockchain-style).
Provides chain verification endpoint to detect any tampering with logs.
"""
import json
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Audit Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path("/app/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
CHAIN_FILE = DATA_DIR / "audit_chain.json"

audit_chain: list[dict] = []


def _load_chain():
    global audit_chain
    if CHAIN_FILE.exists():
        with open(CHAIN_FILE) as f:
            audit_chain = json.load(f)
        logger.info(f"Loaded audit chain: {len(audit_chain)} entries")
    else:
        genesis = {
            "index": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "chain_initialized",
            "prev_hash": "0" * 64,
            "hash": hashlib.sha256(b"genesis_block_zero_trust").hexdigest(),
        }
        audit_chain.append(genesis)
        _persist_chain()
        logger.info("Initialized genesis block in audit chain")


def _persist_chain():
    CHAIN_FILE.write_text(json.dumps(audit_chain, indent=2))


class LogEntry(BaseModel):
    trace_id: str
    agent_id: str
    action_type: str
    target: str
    input_hash: str
    decision: str
    timestamp: str
    decisions: list = []


class ChainVerifyResult(BaseModel):
    valid: bool
    entries_checked: int
    first_invalid_index: int = -1


@app.post("/api/v1/audit/log")
async def log_entry(entry: LogEntry):
    prev_entry = audit_chain[-1]
    prev_hash = prev_entry["hash"]

    raw = f"{entry.timestamp}|{entry.agent_id}|{entry.action_type}|{entry.target}|{entry.decision}|{prev_hash}"
    current_hash = hashlib.sha256(raw.encode()).hexdigest()

    chain_entry = {
        "index": len(audit_chain),
        "trace_id": entry.trace_id,
        "agent_id": entry.agent_id,
        "action_type": entry.action_type,
        "target": entry.target,
        "input_hash": entry.input_hash,
        "decision": entry.decision,
        "timestamp": entry.timestamp,
        "prev_hash": prev_hash,
        "hash": current_hash,
    }

    audit_chain.append(chain_entry)
    _persist_chain()

    log_decision = (
        f"ALLOWED: {entry.agent_id} -> {entry.action_type} on {entry.target}"
        if entry.decision == "ALLOWED"
        else f"DENIED ({entry.decision}): {entry.agent_id} -> {entry.action_type} on {entry.target}"
    )
    logger.info(f"Audit logged [{chain_entry['index']}]: {log_decision}")

    return {"index": chain_entry["index"], "hash": current_hash, "status": "logged"}


@app.get("/api/v1/audit/chain")
async def get_chain(limit: int = 50, offset: int = 0):
    entries = audit_chain[offset:offset + limit]
    return {
        "total": len(audit_chain),
        "offset": offset,
        "limit": limit,
        "entries": entries,
    }


@app.get("/api/v1/audit/chain/verify")
async def verify_chain():
    for i in range(1, len(audit_chain)):
        current = audit_chain[i]
        prev = audit_chain[i - 1]

        expected_prev_hash = prev["hash"]
        if current["prev_hash"] != expected_prev_hash:
            return ChainVerifyResult(
                valid=False,
                entries_checked=i,
                first_invalid_index=i,
            )

        raw = f"{current['timestamp']}|{current['agent_id']}|{current['action_type']}|{current['target']}|{current['decision']}|{expected_prev_hash}"
        expected_hash = hashlib.sha256(raw.encode()).hexdigest()
        if current["hash"] != expected_hash:
            return ChainVerifyResult(
                valid=False,
                entries_checked=i,
                first_invalid_index=i,
            )

    return ChainVerifyResult(valid=True, entries_checked=len(audit_chain))


@app.get("/api/v1/audit/agent/{agent_id}")
async def get_agent_audit(agent_id: str):
    entries = [e for e in audit_chain if e.get("agent_id") == agent_id]
    return {"agent_id": agent_id, "total_actions": len(entries), "entries": entries[-50:]}


@app.get("/api/v1/audit/stats")
async def get_stats():
    total = len(audit_chain) - 1
    allowed = sum(1 for e in audit_chain if e.get("decision") == "ALLOWED")
    denied = sum(1 for e in audit_chain if e.get("decision", "").startswith("DENIED"))
    return {
        "total_actions": total,
        "allowed": allowed,
        "denied": denied,
        "chain_integrity": "verified" if (await verify_chain()).valid else "COMPROMISED",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "audit-service", "chain_length": len(audit_chain)}


@app.get("/")
async def root():
    return {"service": "Audit Service", "version": "1.0.0", "status": "running"}


_load_chain()
