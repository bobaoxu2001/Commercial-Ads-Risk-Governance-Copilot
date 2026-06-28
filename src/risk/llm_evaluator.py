from __future__ import annotations

import json

from src.config import settings


def llm_available() -> bool:
    return bool(settings.openai_api_key)


def evaluate_with_openai(case_payload: dict[str, object]) -> dict[str, object] | None:
    """Optional comparison path; deterministic decisions remain authoritative by default."""
    if not settings.openai_api_key:
        return None
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=settings.openai_model,
        input=[{
            "role": "user",
            "content": (
                "Assess this public-source ad-risk case. Return JSON only with keys risk_category, "
                "risk_score, evidence, policy_rationale, recommended_action, confidence, and needs_human_review. "
                "Do not infer identity or private facts.\n" + json.dumps(case_payload, ensure_ascii=False)
            ),
        }],
    )
    return json.loads(response.output_text)
