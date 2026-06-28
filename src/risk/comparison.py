from __future__ import annotations

import duckdb

from src.config import settings
from src.risk.llm_evaluator import evaluate_with_openai, llm_available

# Fields compared side by side between the deterministic engine and the optional LLM.
_DETERMINISTIC_FIELDS = ("risk_category", "risk_score", "severity", "recommended_action", "confidence")

_SAMPLE_SQL = """
    WITH case_texts AS (
      SELECT case_id, case_text, product FROM cfpb_complaints
      UNION ALL
      SELECT case_id, ad_text, 'commercial advertisement' FROM ads
    )
    SELECT s.case_id, s.source, s.language, s.risk_category, s.risk_score, s.severity,
           s.recommended_action, s.confidence, c.case_text, c.product
    FROM ad_risk_scores s JOIN case_texts c USING (case_id)
    ORDER BY s.risk_score DESC, s.case_id
    LIMIT ?
"""


def _excerpt(text: str, length: int = 220) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= length else f"{text[:length]}…"


def _sample_rows(limit: int) -> list[dict[str, object]]:
    with duckdb.connect(str(settings.db_path), read_only=True) as db:
        frame = db.execute(_SAMPLE_SQL, [limit]).fetchdf()
    frame = frame.where(frame.notna(), None)
    return frame.to_dict("records")


def rule_vs_llm_comparison(limit: int = 5) -> dict[str, object]:
    """Compare deterministic rule output against an optional LLM second opinion.

    Truth boundary: the deterministic engine is authoritative. The LLM is a comparison
    layer only, and no paid request is sent unless OPENAI_API_KEY is configured. When the
    key is absent, every LLM cell is an explicit empty state — nothing is fabricated.
    """
    available = llm_available()
    base = {
        "llm_available": available,
        "llm_model": settings.openai_model if available else None,
        "default_engine": "deterministic_rules_v1",
        "note": (
            "LLM comparison is active. The deterministic engine still produces the authoritative "
            "recommendation; the LLM is a non-binding second opinion for sampled cases."
            if available else
            "No OPENAI_API_KEY is configured, so no LLM call is made. Deterministic rule-based scoring "
            "remains the default for every case; LLM comparison is an optional, opt-in layer."
        ),
    }
    if not settings.db_path.exists():
        return {**base, "status": "unavailable", "reason": "DuckDB mart not built", "sample_size": 0, "cases": []}

    rows = _sample_rows(limit)
    cases: list[dict[str, object]] = []
    for row in rows:
        deterministic = {field: row.get(field) for field in _DETERMINISTIC_FIELDS}
        llm_output: dict[str, object] | None = None
        category_agreement: bool | None = None
        action_agreement: bool | None = None
        if available:
            payload = {
                "case_id": row.get("case_id"),
                "text": row.get("case_text"),
                "product": row.get("product"),
                "source": row.get("source"),
                "language": row.get("language"),
            }
            llm_output = evaluate_with_openai(payload)
            if llm_output:
                category_agreement = llm_output.get("risk_category") == deterministic["risk_category"]
                action_agreement = llm_output.get("recommended_action") == deterministic["recommended_action"]
        cases.append({
            "case_id": row.get("case_id"),
            "source": row.get("source"),
            "language": row.get("language"),
            "excerpt": _excerpt(str(row.get("case_text") or "")),
            "deterministic": deterministic,
            "llm": llm_output,
            "category_agreement": category_agreement,
            "action_agreement": action_agreement,
        })
    agreements = [c["category_agreement"] for c in cases if c["category_agreement"] is not None]
    return {
        **base,
        "status": "available",
        "sample_size": len(cases),
        "category_agreement_rate": round(sum(agreements) / len(agreements), 3) if agreements else None,
        "cases": cases,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(rule_vs_llm_comparison(), ensure_ascii=False, indent=2))
