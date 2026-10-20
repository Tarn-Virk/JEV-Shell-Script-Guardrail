"""Append-only audit log: one JSON line per guardrail decision."""

import json
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path("audit.jsonl")


def log(
    command: str,
    judgement: dict,
    decision: dict,
    executed: bool,
    output: str = "",
) -> dict:
    """Append one line to audit.jsonl and return the full entry."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "command": command,
        "verdict": decision["verdict"],
        "danger_score": decision["danger_score"],
        "executed": executed,
        "judgement": judgement,
        "reasons": decision["reasons"],
        "output": output[:2000],   # cap long output so the log doesn't bloat
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def read_recent(limit: int = 20) -> list[dict]:
    """Return the most recent `limit` entries, newest first."""
    if not LOG_PATH.exists():
        return []
    lines = LOG_PATH.read_text(encoding="utf-8").strip().split("\n")
    recent = [line for line in lines[-limit:] if line]
    return [json.loads(line) for line in recent][::-1]
