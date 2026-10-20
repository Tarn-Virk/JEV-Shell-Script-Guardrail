"""Append a few audit entries, read them back."""
from jev_guardrail.audit import log, read_recent

# Simulate 3 decisions
log(
    command="ls -la",
    judgement={"destructive": 0.01, "risk_category": "safe"},
    decision={"verdict": "allow", "danger_score": 0.01, "reasons": ["safe"]},
    executed=True,
    output="total 24\ndrwxr-xr-x ...",
)

log(
    command="git reset --hard HEAD~5",
    judgement={"destructive": 0.9, "risk_category": "block"},
    decision={"verdict": "review", "danger_score": 0.64, "reasons": ["destructive but not catastrophic"]},
    executed=False,
)

log(
    command="rm -rf /",
    judgement={"destructive": 0.99, "risk_category": "block"},
    decision={"verdict": "block", "danger_score": 0.94, "reasons": ["catastrophic"]},
    executed=False,
)

# Read back
print("Last 3 entries (newest first):")
for entry in read_recent(3):
    print(f"  [{entry['ts']}] {entry['verdict'].upper():6}  {entry['command']}")
