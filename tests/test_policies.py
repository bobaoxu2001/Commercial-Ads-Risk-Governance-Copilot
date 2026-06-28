from src.risk.policy_retriever import load_policy_rules, retrieve_policy_rules


def test_policy_knowledge_base_has_sources() -> None:
    rules = load_policy_rules()
    assert len(rules) >= 10
    assert all(rule.source_url.startswith("https://") for rule in rules)
    assert all(rule.last_checked != "unknown" for rule in rules)


def test_retrieval_returns_category_rule() -> None:
    rules = retrieve_policy_rules("Financial Scam / High-Risk Financial Services")
    assert rules
    assert rules[0].rule_id == "TT-FIN-001"
