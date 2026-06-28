from __future__ import annotations

from datetime import UTC, datetime

import duckdb

from src.config import settings


def evaluation_metrics() -> dict[str, object]:
    if not settings.db_path.exists():
        return {"status": "unavailable", "reason": "DuckDB mart not built"}
    with duckdb.connect(str(settings.db_path), read_only=True) as db:
        scores = db.execute("SELECT * FROM ad_risk_scores").fetchdf()
        feedback = db.execute("SELECT * FROM human_review_feedback").fetchdf()
    if scores.empty:
        return {"status": "unavailable", "reason": "No cases scored"}
    escalation = float((scores["recommended_action"] == "escalate to human review").mean())
    auto_coverage = float((scores["recommended_action"] != "escalate to human review").mean())
    completeness = float(scores["evidence_json"].fillna("[]").ne("[]").mean())
    auto_cases = int((scores["recommended_action"] != "escalate to human review").sum())
    result: dict[str, object] = {
        "status": "available",
        "scored_cases": len(scores),
        "escalation_rate": round(escalation, 3),
        "auto_decision_coverage": round(auto_coverage, 3),
        "evidence_extraction_completeness": round(completeness, 3),
        "estimated_review_minutes_saved": auto_cases * 3,
        "labeled_cases": len(feedback),
        "precision": None,
        "recall": None,
        "f1": None,
        "label_note": "Precision/recall/F1 appear only after reviewer labels exist.",
    }
    if not feedback.empty:
        latest = feedback.sort_values("created_at").drop_duplicates("case_id", keep="last")
        joined = scores.merge(latest[["case_id", "reviewer_decision"]], on="case_id", how="inner")
        usable = joined[joined["reviewer_decision"].isin(["approve", "reject", "false positive", "false negative"])]
        if not usable.empty:
            predicted = usable["risk_score"] >= 0.65
            actual = usable["reviewer_decision"].isin(["reject", "false negative"])
            tp = int((predicted & actual).sum())
            fp = int((predicted & ~actual).sum())
            fn = int((~predicted & actual).sum())
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
            result.update({"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3), "label_note": "Metrics use the latest usable reviewer decision per case."})
    return result


def write_report() -> None:
    result = evaluation_metrics()
    metrics = "\n".join(f"- **{key.replace('_', ' ').title()}:** {value}" for key, value in result.items())
    text = f"""# Evaluation Report

Generated: {datetime.now(UTC).isoformat()}

This report is calculated from the current local DuckDB mart. It never substitutes fabricated labels. Precision, recall, and F1 remain unavailable until human review feedback exists.

## Current deterministic workflow

{metrics}

## Rule vs. LLM comparison

The deterministic rules engine is the default and is evaluated for every case. If `OPENAI_API_KEY` is configured, `src/risk/llm_evaluator.py` can produce a second structured assessment for sampled-case comparison; no paid call is made by default.

## Interpretation limits

CFPB complaints are not verified examples of policy-violating ads, and FTC rows are aggregates. These sources provide consumer-harm priors and vocabulary, not ground-truth ad enforcement labels. Human review remains required for ambiguous decisions.
"""
    (settings.root / "docs" / "EVALUATION_REPORT.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    write_report()
