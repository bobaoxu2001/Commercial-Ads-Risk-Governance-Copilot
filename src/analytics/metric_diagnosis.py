from __future__ import annotations

import duckdb
import pandas as pd

from src.analytics.anomaly_detection import daily_anomalies
from src.analytics.feature_lift import calculate_feature_lift
from src.config import settings


def metric_diagnosis() -> dict[str, object]:
    if not settings.db_path.exists():
        return {"category_distribution": [], "language_comparison": [], "market_comparison": [], "action_coverage": [], "feature_lift": [], "anomalies": []}
    with duckdb.connect(str(settings.db_path), read_only=True) as db:
        scores = db.execute("SELECT * FROM ad_risk_scores").fetchdf()
        markets = db.execute("""
            SELECT c.state, count(*) cases, avg(CASE WHEN s.risk_score >= 0.65 THEN 1.0 ELSE 0.0 END) high_risk_rate
            FROM ad_risk_scores s JOIN cfpb_complaints c USING (case_id)
            WHERE c.state IS NOT NULL AND c.state <> ''
            GROUP BY c.state HAVING count(*) >= 5 ORDER BY cases DESC LIMIT 12
        """).fetchdf()
    category = scores.groupby("risk_category").size().rename("cases").reset_index().sort_values("cases", ascending=False).to_dict("records") if not scores.empty else []
    language = scores.groupby("language").agg(cases=("case_id", "size"), high_risk_rate=("risk_score", lambda values: round(float((values >= 0.65).mean()), 3))).reset_index().to_dict("records") if not scores.empty else []
    action = scores.groupby("recommended_action").size().rename("cases").reset_index().to_dict("records") if not scores.empty else []
    return {"category_distribution": category, "language_comparison": language, "market_comparison": markets.to_dict("records"), "action_coverage": action, "feature_lift": calculate_feature_lift(scores), "anomalies": daily_anomalies(scores)}
