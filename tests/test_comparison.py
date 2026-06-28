from src.risk.comparison import rule_vs_llm_comparison


def test_comparison_is_deterministic_default_without_key() -> None:
    """Without OPENAI_API_KEY, the LLM column must stay empty and nothing is fabricated."""
    result = rule_vs_llm_comparison(limit=3)
    assert result["llm_available"] is False
    assert result["llm_model"] is None
    assert result["default_engine"] == "deterministic_rules_v1"
    assert isinstance(result["cases"], list)
    assert result["sample_size"] == len(result["cases"])

    if result["status"] == "available":
        # Mart is built: each sampled case has deterministic output and an empty LLM cell.
        for case in result["cases"]:
            assert case["deterministic"]["risk_category"]
            assert case["llm"] is None
            assert case["category_agreement"] is None
    else:
        # Mart not built (e.g. CI before ingest): clean empty state, no fabricated cases.
        assert result["status"] == "unavailable"
        assert result["cases"] == []
