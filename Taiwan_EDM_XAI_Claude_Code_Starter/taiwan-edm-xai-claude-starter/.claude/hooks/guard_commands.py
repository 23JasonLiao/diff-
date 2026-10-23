"""Example best-effort unsafe command guard. NOT a sandbox/security boundary."""
import json
import re
import sys

payload = json.load(sys.stdin)
command = str(payload.get("tool_input", {}).get("command", ""))
patterns = [
    (r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f\b", "Recursive force removal"),
    (r"\bgit\s+reset\s+--hard\b", "Irreversible git reset"),
    (r"\bgit\s+push\s+--force\b", "Force git push"),
    (r"\bgit\s+clean\s+-[a-zA-Z]*f", "Destructive git clean"),
    (r"--dangerously-skip-permissions", "Unsafe agent permissions bypass"),
]
for regex, reason in patterns:
    if re.search(regex, command, re.IGNORECASE):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Project hook blocked: {reason}. Request user approval and use a safer alternative."
            }
        }))
        break
