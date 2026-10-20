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
