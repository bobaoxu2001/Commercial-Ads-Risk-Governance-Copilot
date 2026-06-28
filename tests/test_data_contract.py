import pandas as pd

from src.risk.taxonomy import CATEGORY_NAMES


def test_required_score_contract() -> None:
    columns = {
        "case_id", "language", "risk_score", "risk_category", "severity", "policy_rationale",
        "recommended_action", "confidence", "business_impact_note", "needs_human_review",
    }
    frame = pd.DataFrame([{name: None for name in columns}])
    assert columns.issubset(frame.columns)
    assert "Financial Scam / High-Risk Financial Services" in CATEGORY_NAMES
