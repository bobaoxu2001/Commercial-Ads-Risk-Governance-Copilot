from __future__ import annotations

import json
from collections import Counter

import pandas as pd


def calculate_feature_lift(scores: pd.DataFrame) -> list[dict[str, object]]:
    if scores.empty:
        return []
    all_terms: Counter[str] = Counter()
    high_terms: Counter[str] = Counter()
    high_mask = scores["risk_score"] >= 0.65
    for idx, value in scores["evidence_json"].items():
        terms = {item.get("term", "") for item in json.loads(value or "[]") if item.get("term")}
        all_terms.update(terms)
        if bool(high_mask.loc[idx]):
            high_terms.update(terms)
    high_total = max(1, int(high_mask.sum()))
    total = max(1, len(scores))
    rows = []
    for term, count in all_terms.items():
        high_count = high_terms[term]
        lift = (high_count / high_total) / max(count / total, 1 / total)
        rows.append({"term": term, "cases": count, "high_risk_cases": high_count, "lift": round(lift, 2)})
    return sorted(rows, key=lambda row: (row["lift"], row["high_risk_cases"]), reverse=True)[:12]
