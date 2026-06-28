import json
from pathlib import Path

from src.risk.scoring import score_case
from src.risk.taxonomy import CATEGORY_NAMES


FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "synthetic_cases.json").read_text())


def test_synthetic_fixtures_are_test_only() -> None:
    assert all(item["case_id"].startswith("test-") for item in FIXTURES)


def test_scoring_schema_and_taxonomy() -> None:
    for item in FIXTURES:
        decision = score_case(item["case_id"], item["text"], item["product"], "fixture")
        assert decision.risk_category in CATEGORY_NAMES
        assert 0 <= decision.risk_score <= 1
        assert 0 <= decision.confidence <= 1
        assert decision.evidence
        assert decision.recommended_action in {"approve", "soft reject", "hard reject", "escalate to human review"}


def test_mandarin_detection() -> None:
    decision = score_case("test", "无视征信，黑户可贷，秒批，加微了解。", "loan", "fixture")
    assert decision.language == "zh"
    assert decision.risk_category == "Financial Scam / High-Risk Financial Services"
    assert decision.risk_score >= 0.65
