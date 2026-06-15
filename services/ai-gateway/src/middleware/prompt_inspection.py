"""
Stage 4 of the middleware pipeline: Prompt Inspection.
Scans agent inputs for prompt injection attacks and data exfiltration attempts.
Uses regex pattern matching against known jailbreak and leak patterns.
Returns 400 if dangerous content is detected before the action executes.
"""
import re
import logging

logger = logging.getLogger(__name__)


INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|directions|commands)",
    r"forget\s+(all\s+)?(previous|prior)\s+(instructions|directions|commands)",
    r"you\s+are\s+(now|not\s+bound|free)",
    r"override\s+(your\s+)?(instructions|programming|directives)",
    r"system\s+(prompt|instruction|message)",
    r"disregard\s+(all\s+)?(rules|policies|safety)",
    r"simulate\s+(a\s+)?(different|new)\s+(persona|role|character)",
    r"DAN\b",  # "Do Anything Now" jailbreak
    r"role[-\s]?play",
    r"sudo\s+mode",
    r"developer\s+mode",
    r"pretend\s+(you\s+are|to\s+be)",
    r"reveal\s+(your\s+)?(system|prompt|instructions)",
    r"output\s+your\s+(prompt|instructions|system\s+message)",
    r"leak\s+(the\s+)?(prompt|api[-\s]?key|secret|token|password)",
    r"[\w\.\-]+@[\w\.\-]+\.\w{2,}",  # email exfiltration pattern
]

EXFILTRATION_PATTERNS = [
    r"(credit\s*card|ssn|social\s*security|passport)",
    r"(api[-\s]?key|secret\s*key|access\s*token)",
    r"(password|passwd|pwd)\s*[:=]\s*\S+",
]


class PromptInspectionMiddleware:
    async def inspect(self, agent_id: str, action_type: str, target: str, payload: dict) -> dict:
        text_to_check = str(payload) + " " + target

        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, text_to_check, re.IGNORECASE):
                logger.warning(f"Prompt injection detected for {agent_id}: matched '{pattern}'")
                return {
                    "allowed": False,
                    "reason": f"prompt injection detected: input matches prohibited pattern",
                    "component": "prompt_inspection",
                }

        for pattern in EXFILTRATION_PATTERNS:
            if re.search(pattern, text_to_check, re.IGNORECASE):
                logger.warning(f"Exfiltration attempt detected for {agent_id}: matched '{pattern}'")
                return {
                    "allowed": False,
                    "reason": f"data exfiltration attempt detected",
                    "component": "prompt_inspection",
                }

        return {"allowed": True}
