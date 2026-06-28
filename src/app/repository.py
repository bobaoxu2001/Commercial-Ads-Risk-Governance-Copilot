from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import duckdb

from src.analytics.evaluate import evaluation_metrics
from src.analytics.metric_diagnosis import metric_diagnosis
from src.config import settings
from src.risk.taxonomy import MANDARIN_TERMS


def _connect(read_only: bool = True) -> duckdb.DuckDBPyConnection:
    if not settings.db_path.exists():
        raise FileNotFoundError("Data mart is missing. Run `make ingest && make transform`.")
    return duckdb.connect(str(settings.db_path), read_only=read_only)


def _records(db: duckdb.DuckDBPyConnection, sql: str, params: list[object] | None = None) -> list[dict[str, object]]:
    frame = db.execute(sql, params or []).fetchdf()
    frame = frame.where(frame.notna(), None)
    return frame.to_dict("records")


def overview() -> dict[str, object]:
    with _connect() as db:
        counts = db.execute("SELECT (SELECT count(*) FROM cfpb_complaints), (SELECT count(*) FROM ftc_fraud_categories), (SELECT count(*) FROM ads), (SELECT count(*) FROM ad_risk_scores)").fetchone()
        high = db.execute("SELECT count(*) FROM ad_risk_scores WHERE risk_score >= 0.65").fetchone()[0]
        review = db.execute("SELECT count(*) FROM ad_risk_scores WHERE needs_human_review").fetchone()[0]
        auto_cases = db.execute("SELECT count(*) FROM ad_risk_scores WHERE recommended_action <> 'escalate to human review'").fetchone()[0]
        latest = db.execute("SELECT max(evaluated_at) FROM ad_risk_scores").fetchone()[0]
        retrieval = db.execute("SELECT retrieval_path FROM cfpb_complaints LIMIT 1").fetchone()
    cfpb_count, ftc_count, ads_count, scored = map(int, counts)
    return {
        "total_real_records": cfpb_count + ftc_count + ads_count,
        "cases_analyzed": scored,
        "high_risk_cases": int(high),
        "high_risk_rate": round(high / scored, 3) if scored else 0,
        "review_queue_size": int(review),
        "estimated_minutes_saved": int(auto_cases) * 3,
        "last_updated": str(latest) if latest else None,
        "sources": [
            {"key": "ftc", "name": "FTC Consumer Sentinel", "records": ftc_count, "status": "loaded", "detail": "Official 2024 aggregate archive"},
            {"key": "cfpb", "name": "CFPB Complaints", "records": cfpb_count, "status": "loaded", "detail": (retrieval[0] if retrieval else "unknown").replace("_", " ")},
            {"key": "meta", "name": "Meta Ad Library", "records": ads_count, "status": "loaded" if ads_count else "optional", "detail": "Official API token required"},
        ],
    }


def cases(search: str = "", category: str = "", severity: str = "", language: str = "", source: str = "", action: str = "", limit: int = 200) -> list[dict[str, object]]:
    sql = """
        WITH case_texts AS (
          SELECT case_id, case_text, product, issue, state, 'CFPB' source_name, source_url FROM cfpb_complaints
          UNION ALL
          SELECT case_id, ad_text, 'Commercial ad', advertiser_name, NULL, 'Meta', source_url FROM ads
        )
        SELECT s.case_id, s.source, s.case_date, s.language, s.risk_score, s.risk_category,
               s.severity, s.recommended_action, s.needs_human_review, c.case_text, c.product,
               c.issue, c.state, c.source_url
        FROM ad_risk_scores s JOIN case_texts c USING (case_id)
        WHERE (? = '' OR lower(c.case_text) LIKE '%' || lower(?) || '%')
          AND (? = '' OR s.risk_category = ?)
          AND (? = '' OR s.severity = ?)
          AND (? = '' OR s.language = ?)
          AND (? = '' OR s.source = ?)
          AND (? = '' OR s.recommended_action = ?)
        ORDER BY s.risk_score DESC, s.case_date DESC NULLS LAST LIMIT ?
    """
    params = [search, search, category, category, severity, severity, language, language, source, source, action, action, limit]
    with _connect() as db:
        return _records(db, sql, params)


def case_detail(case_id: str) -> dict[str, object] | None:
    matching = cases(search="", limit=10000)
    base = next((row for row in matching if row["case_id"] == case_id), None)
    if not base:
        return None
    with _connect() as db:
        score = _records(db, "SELECT * FROM ad_risk_scores WHERE case_id = ?", [case_id])[0]
        rule_ids = json.loads(score.get("matched_policy_rule_ids_json") or "[]")
        policies = _records(db, "SELECT * FROM policy_rules WHERE rule_id IN (SELECT unnest(?::VARCHAR[]))", [rule_ids]) if rule_ids else []
        feedback = _records(db, "SELECT * FROM human_review_feedback WHERE case_id = ? ORDER BY created_at DESC", [case_id])
    score["evidence"] = json.loads(score.pop("evidence_json") or "[]")
    score["matched_policy_rule_ids"] = rule_ids
    return {**base, **score, "policies": policies, "feedback": feedback}


def save_feedback(case_id: str, decision: str, notes: str = "") -> dict[str, object]:
    allowed = {"approve", "reject", "escalate", "wrong category", "false positive", "false negative"}
    if decision not in allowed:
        raise ValueError("Unsupported reviewer decision")
    payload = {"feedback_id": str(uuid.uuid4()), "case_id": case_id, "reviewer_decision": decision, "notes": notes, "created_at": datetime.now(UTC).isoformat()}
    with _connect(read_only=False) as db:
        db.execute("INSERT INTO human_review_feedback VALUES (?, ?, ?, ?, ?)", list(payload.values()))
    return payload


def metrics() -> dict[str, object]:
    return {**metric_diagnosis(), "evaluation": evaluation_metrics()}


def policies() -> list[dict[str, object]]:
    with _connect() as db:
        return _records(db, "SELECT * FROM policy_rules ORDER BY category, rule_id")


def mandarin_lab() -> dict[str, object]:
    terms = [{"term": term, "pinyin": values[0], "gloss": values[1], "category": values[2]} for term, values in MANDARIN_TERMS.items()]
    examples = []
    for row in cases(limit=10000):
        matches = [term for term in MANDARIN_TERMS if term in (row.get("case_text") or "")]
        if matches:
            examples.append({"case_id": row["case_id"], "source": row["source"], "matches": matches, "excerpt": row["case_text"][:240]})
    return {"terms": terms, "real_record_examples": examples[:20], "note": "Terms are contextual signals. Pinyin, homophones, character splitting, and off-platform prompts can evade literal keyword matching."}
