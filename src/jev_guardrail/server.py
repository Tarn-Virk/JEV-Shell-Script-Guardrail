"""FastAPI backend: judges shell commands and executes allowed ones in a sandbox."""

import subprocess
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from jev_guardrail.judge import judge
from jev_guardrail.policy import decide
from jev_guardrail.audit import log, read_recent


app = FastAPI(title="JEV Shell Guardrail")

# All executed commands run inside this folder. Nothing else gets touched.
SANDBOX = Path("sandbox").resolve()
SANDBOX.mkdir(exist_ok=True)

STATIC = Path(__file__).parent / "static"


class RunRequest(BaseModel):
    command: str
    approved: bool = False


@app.post("/run")
def run_command(req: RunRequest):
    judgement = judge(req.command)
    decision = decide(judgement)
    verdict = decision["verdict"]

    should_run = (verdict == "allow") or (verdict == "review" and req.approved)
    output = ""

    if should_run:
        try:
            result = subprocess.run(
                req.command,
                shell=True,
                cwd=str(SANDBOX),
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = (result.stdout or "") + (result.stderr or "")
        except subprocess.TimeoutExpired:
            output = "[timed out after 10s]"
        except Exception as e:
            output = f"[error running command: {e}]"

    entry = log(
        command=req.command,
        judgement=judgement,
        decision=decision,
        executed=should_run,
        output=output,
    )

    return {
        "verdict": verdict,
        "danger_score": decision["danger_score"],
        "reasons": decision["reasons"],
        "judgement": judgement,
        "executed": should_run,
        "output": output,
        "ts": entry["ts"],
    }


@app.get("/audit")
def get_audit(limit: int = 20):
    return {"entries": read_recent(limit)}


app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


@app.get("/")
def index():
    html = STATIC / "index.html"
    if html.exists():
        return FileResponse(html)
    return {"message": "Frontend not built yet."}
