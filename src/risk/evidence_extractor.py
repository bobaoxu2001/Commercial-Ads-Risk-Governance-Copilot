from __future__ import annotations

import re

from src.risk.taxonomy import CATEGORIES

SIGNAL_GROUPS = {
    "urgency_or_guarantee": ("guaranteed", "instant", "limited time", "act now", "100%", "稳赚", "保本", "秒批"),
    "regulated_product": ("loan", "credit", "investment", "crypto", "pharmacy", "supplement", "gambling", "mortgage", "student loan"),
    "off_platform_contact": ("whatsapp", "telegram", "wechat", "dm me", "加微", "私域", "引流"),
}


def contains_term(text: str, term: str) -> bool:
    if re.search(r"[A-Za-z]", term):
        return bool(re.search(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", text, flags=re.IGNORECASE))
    return term in text


def detect_language(text: str) -> str:
    has_zh = bool(re.search(r"[\u4e00-\u9fff]", text))
    has_en = bool(re.search(r"[A-Za-z]", text))
    return "mixed" if has_zh and has_en else "zh" if has_zh else "en"


def extract_evidence(text: str) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for signal_type, terms in SIGNAL_GROUPS.items():
        for term in terms:
            if contains_term(text, term) and (signal_type, term) not in seen:
                found.append({"type": signal_type, "term": term, "excerpt": term})
                seen.add((signal_type, term))
    for category in CATEGORIES:
        for term in category.keywords:
            if contains_term(text, term) and (category.name, term) not in seen:
                found.append({"type": "taxonomy_match", "term": term, "category": category.name, "excerpt": term})
                seen.add((category.name, term))
    return found


def landing_page_mismatch(ad_text: str, landing_text: str | None) -> dict[str, str] | None:
    if not landing_text:
        return None
    ad_tokens = set(re.findall(r"[A-Za-z\u4e00-\u9fff]{2,}", ad_text.lower()))
    landing_tokens = set(re.findall(r"[A-Za-z\u4e00-\u9fff]{2,}", landing_text.lower()))
    overlap = len(ad_tokens & landing_tokens) / max(1, len(ad_tokens))
    if overlap < 0.18:
        return {"type": "landing_page_mismatch", "term": "low semantic overlap", "category": "Landing Page Mismatch", "excerpt": f"Token overlap {overlap:.0%}"}
    return None
