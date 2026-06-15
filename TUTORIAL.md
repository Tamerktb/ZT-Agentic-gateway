# Zero Trust AI Gateway — Tutorial

This tutorial walks through the project file by file.
By the end, you will understand:

- How Zero Trust works in practice
- How JWTs authenticate AI agents
- How policy engines control what agents can do
- How prompt injection attacks work and how to block them
- How immutable audit logs catch tampering

---

## Prerequisites

- Python 3.9+ installed
- `pip install fastapi uvicorn httpx pydantic pydantic-settings PyJWT`

---

## Part 1: The 5-Stage Pipeline

Every action an AI agent takes passes through 5 security stages.
Open `services/ai-gateway/src/routers/agents.py` — this is where it happens.

```
Request → ① Authenticate (JWT) → ② Policy Check → ③ Rate Limit → ④ Prompt Inspection → ⑤ Audit Log → Response
```

Open each middleware file in `services/ai-gateway/src/middleware/` to see the code:

| File | Stage | What it checks |
|------|-------|----------------|
| `auth.py` | 1 | Is this agent who they claim? (JWT verification) |
| `policy.py` | 2 | Does this agent have permission? (role-tool mapping) |
| `rate_limit.py` | 3 | Is this agent spamming? (10 actions/min, $1000/hr) |
| `prompt_inspection.py` | 4 | Is the agent being tricked? (injection + exfiltration patterns) |
| `audit.py` | 5 | Record everything for later investigation |

**Try it:** Read `auth.py` — 24 lines. See how it calls the Identity Provider to verify the JWT?

---

## Part 2: Identity Provider — Non-Human Identities (NHIs)

Open `services/identity-provider/src/main.py`.

An NHI is like an employee badge, but for an AI agent. It contains:
- Who the agent is (`agent_id`)
- What role it has (`shopping_agent`, `data_processor`, etc.)
- What tools it can access (`policies`)

The three key endpoints:

```python
POST /api/v1/nhi/register   # Create an agent identity
POST /api/v1/nhi/token      # Issue a JWT for that identity
POST /api/v1/nhi/verify     # Check if a JWT is valid
```

**Try it:** Register an agent and get its token:

```bash
curl -X POST http://localhost:8001/api/v1/nhi/register \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"my-bot","role":"shopping_agent","policies":["check_inventory"]}'

curl -X POST http://localhost:8001/api/v1/nhi/token \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"my-bot","role":"shopping_agent","policies":["check_inventory"]}'
```

---

## Part 3: Policy Engine — What Can Agents Do?

Open `services/policy-engine/policies/agent_policy.rego`.

This file defines which tools each role can access:

```python
shopping_agent = ["purchase_item", "check_inventory", "refund_order"]
data_processor = ["read_dataset", "transform_data", "generate_report"]
email_agent    = ["send_email", "read_inbox"]
```

Open `services/policy-engine/policies/tool_policy.rego` to see per-tool restrictions:

```python
"purchase_item": { "max_amount": 500 },        # Can't spend >$500
"refund_order":  { "require_mfa": true },       # Needs human approval
"delete_user":   { "require_mfa": true }        # Sensitive action
```

**Try it:** See what happens when a shopping agent tries to delete a user:

```bash
curl -X POST http://localhost:8003/api/v1/policy/evaluate \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"shopping-agent","action_type":"call_tool","target":"delete_user","payload":{},"role":"shopping_agent"}'
```

Expected response: `{"allowed":false, "reason":"agent role 'shopping_agent' not authorized for tool 'delete_user'"}`

---

## Part 4: Prompt Inspection — Blocking AI Attacks

Open `services/ai-gateway/src/middleware/prompt_inspection.py`.

This is the most "2026" part of the project. It uses regex patterns to detect two types of attacks:

**Injection patterns** — attackers trying to override the AI's instructions:
```
"ignore previous instructions"
"you are now in developer mode"
"override your programming"
"DAN" (Do Anything Now jailbreak)
```

**Exfiltration patterns** — attackers trying to steal data:
```
"credit card numbers"
"send to attacker@evil.com"
"api_key = ..."
```

**Try it:** Copy any pattern from `INJECTION_PATTERNS` and search for it in the Wikipedia page for "prompt injection" to see real examples.

---

## Part 5: Audit Service — Tamper-Proof Logs

Open `services/audit-service/src/main.py`.

This implements a blockchain-style hash chain (like Bitcoin, but simpler):

```python
# Each entry contains a SHA256 hash of the previous entry:
hash = SHA256(timestamp + agent_id + action + decision + prev_hash)
```

If someone modifies an old log entry, the hash chain breaks, and `GET /api/v1/audit/chain/verify` returns `valid: false`.

**Try it:** View the audit chain:

```bash
curl http://localhost:8004/api/v1/audit/chain | python -m json.tool
```

Each entry shows: action taken, decision (ALLOWED or DENIED), and the hash pointing to the previous entry.

---

## Running the Attack Simulator

Start all services:
```bash
python test_integration.py
```

This runs 24 automated tests and shuts down. To keep services running:

```bash
# Start each service in a separate terminal:
cd services/identity-provider && python -m uvicorn src.main:app --host 127.0.0.1 --port 8001
cd services/credential-vault && python -m uvicorn src.main:app --host 127.0.0.1 --port 8002
cd services/policy-engine    && python -m uvicorn src.main:app --host 127.0.0.1 --port 8003
cd services/audit-service    && python -m uvicorn src.main:app --host 127.0.0.1 --port 8004
cd services/ai-gateway       && python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

Then run the attack simulator:
```bash
python services/attack-simulator/attack_simulator.py
```

Or use the web UI:
```bash
python ui/server.py
# Open http://127.0.0.1:8080
```

---

## Extending the Project

**Add a new attack pattern:**
Open `services/ai-gateway/src/middleware/prompt_inspection.py` and add to `INJECTION_PATTERNS`:
```python
r"new\s+dangerous\s+pattern",
```

**Add a new tool:**
Open `services/policy-engine/policies/tool_policy.rego` and add:
```python
"my_tool": { "max_amount": 0, "require_mfa": false, "restrict_actions": ["call_tool"] },
```

**Add a new agent role:**
Open `services/policy-engine/policies/agent_policy.rego` and add:
```python
"analyst": ["read_dataset", "generate_report"],
```

---

## Summary

| Concept | File | What you learned |
|---------|------|-----------------|
| Zero Trust | `services/ai-gateway/src/routers/agents.py` | 5-stage middleware pipeline |
| JWT Auth | `services/identity-provider/src/main.py` | How agents prove identity |
| Policy | `services/policy-engine/policies/*.rego` | Role-based access control |
| Rate limiting | `services/ai-gateway/src/middleware/rate_limit.py` | Prevent runaway agents |
| Prompt injection | `services/ai-gateway/src/middleware/prompt_inspection.py` | How jailbreak attacks work |
| Audit chain | `services/audit-service/src/main.py` | Tamper-proof logging |
