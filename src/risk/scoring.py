from __future__ import annotations

from dataclasses import asdict, dataclass

from src.risk.evidence_extractor import contains_term, detect_language, extract_evidence, landing_page_mismatch
from src.risk.policy_retriever import retrieve_policy_rules
from src.risk.taxonomy import CATEGORIES, category_for_product


@dataclass(frozen=True)
class RiskDecision:
    case_id: str
    language: str
    risk_score: float
    risk_category: str
    severity: str
    evidence: list[dict[str, str]]
    policy_rationale: str
    matched_policy_rule_ids: list[str]
    recommended_action: str
    confidence: float
    business_impact_note: str
    needs_human_review: bool
    engine: str = "deterministic_rules_v1"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _category(text: str, product: str, evidence: list[dict[str, str]]) -> str:
    counts: dict[str, int] = {}
    for item in evidence:
        category = item.get("category")
        if category:
            counts[category] = counts.get(category, 0) + 1
    if counts:
        return max(counts, key=counts.get)
    combined = f"{product} {text}"
    for category in CATEGORIES:
        if any(contains_term(combined, term) for term in category.keywords):
            return category.name
    return category_for_product(product)


def score_case(case_id: str, text: str, product: str = "", source: str = "cfpb", landing_text: str | None = None) -> RiskDecision:
    evidence = extract_evidence(text)
    mismatch = landing_page_mismatch(text, landing_text)
    if mismatch:
        evidence.append(mismatch)
    category = _category(text, product, evidence)
    finance_prior = 0.22 if source == "cfpb" else 0.08
    score = min(0.98, 0.12 + finance_prior + len(evidence) * 0.115)
    if category in {"Dangerous Products or Services", "Adult / Sexualized Content"}:
        score = min(0.98, score + 0.12)
    severity = "critical" if score >= 0.85 else "high" if score >= 0.65 else "medium" if score >= 0.4 else "low"
    confidence = min(0.96, 0.5 + len(evidence) * 0.07 + (0.08 if product else 0.0))
    needs_human_review = 0.4 <= score < 0.85 or confidence < 0.68
    action = "hard reject" if score >= 0.85 and confidence >= 0.75 else "soft reject" if score >= 0.7 else "escalate to human review" if needs_human_review else "approve"
    rules = retrieve_policy_rules(category)
    rationale = rules[0].summary if rules else "No category-specific rule is available; escalate for policy review."
    return RiskDecision(
        case_id=case_id,
        language=detect_language(text),
        risk_score=round(score, 3),
        risk_category=category,
        severity=severity,
        evidence=evidence,
        policy_rationale=rationale,
        matched_policy_rule_ids=[rule.rule_id for rule in rules],
        recommended_action=action,
        confidence=round(confidence, 3),
        business_impact_note="Prioritizes likely consumer-harm cases while retaining human review for ambiguous or context-dependent signals.",
        needs_human_review=needs_human_review,
    )
