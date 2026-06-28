from __future__ import annotations

import json
from datetime import UTC, datetime

import requests

from src.config import settings
from src.ingest.common import timestamp, write_manifest

KEYWORDS = [
    "financial scam", "loan", "investment", "crypto", "weight loss", "supplement",
    "pharmacy", "immigration", "job offer", "gambling", "AI tool", "miracle cure",
    "debt relief", "credit repair",
]


def fetch_meta_ads() -> dict[str, object]:
    out = settings.raw_dir / "meta_ads" / timestamp()
    out.mkdir(parents=True, exist_ok=True)
    if not settings.meta_access_token:
        manifest = {
            "source": "Meta Ad Library API",
            "retrieved_at": datetime.now(UTC).isoformat(),
            "status": "skipped_no_token",
            "records": 0,
            "note": "Set META_ACCESS_TOKEN to enable official API enrichment; no fallback ads are fabricated.",
        }
        write_manifest(out, manifest)
        print("Meta: skipped (META_ACCESS_TOKEN is not set)")
        return manifest
    endpoint = f"https://graph.facebook.com/{settings.meta_graph_api_version}/ads_archive"
    total = 0
    for keyword in KEYWORDS:
        params = {
            "access_token": settings.meta_access_token,
            "ad_reached_countries": json.dumps([settings.meta_ad_country]),
            "ad_type": "ALL",
            "search_terms": keyword,
            "fields": "id,ad_creation_time,ad_creative_bodies,ad_creative_link_captions,ad_creative_link_descriptions,ad_creative_link_titles,page_id,page_name,publisher_platforms,ad_delivery_start_time,ad_delivery_stop_time",
            "limit": 100,
        }
        response = requests.get(endpoint, params=params, timeout=60)
        response.raise_for_status()
        payload = response.json()
        total += len(payload.get("data", []))
        safe_name = keyword.replace(" ", "_")
        (out / f"{safe_name}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    manifest = {
        "source": "Official Meta Ad Library API",
        "endpoint": endpoint,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "status": "complete",
        "records": total,
        "keywords": KEYWORDS,
        "country": settings.meta_ad_country,
    }
    write_manifest(out, manifest)
    print(f"Meta: saved {total} real ads to {out}")
    return manifest


if __name__ == "__main__":
    fetch_meta_ads()
