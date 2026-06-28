from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from src.config import settings

COLUMNS = ["ad_id", "case_id", "ad_text", "advertiser_id", "advertiser_name", "created_at", "delivery_start", "delivery_stop", "platforms", "source", "source_url", "retrieved_at"]


def normalize_ads(raw_dir: Path | None = None, processed_dir: Path | None = None) -> pd.DataFrame:
    """Normalize real Meta Ad Library responses into a tabular ads frame.

    Only `data` entries from saved API responses are read. When no token was supplied,
    the raw run holds a skipped manifest with no `data`, so this returns an empty frame
    with the full schema rather than fabricating any ad records.
    """
    raw_dir = raw_dir or settings.raw_dir
    processed_dir = processed_dir or settings.processed_dir
    rows: list[dict[str, object]] = []
    for path in sorted((raw_dir / "meta_ads").glob("*/*.json")):
        if path.name == "manifest.json":
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        retrieved_at = datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()
        for ad in payload.get("data", []):
            parts = []
            for field in ("ad_creative_bodies", "ad_creative_link_titles", "ad_creative_link_descriptions", "ad_creative_link_captions"):
                parts.extend(ad.get(field) or [])
            text = " ".join(dict.fromkeys(str(part).strip() for part in parts if str(part).strip()))
            if not text:
                continue
            ad_id = str(ad.get("id", ""))
            rows.append({
                "ad_id": ad_id,
                "case_id": f"meta-{ad_id}",
                "ad_text": text,
                "advertiser_id": str(ad.get("page_id", "")),
                "advertiser_name": str(ad.get("page_name", "")),
                "created_at": ad.get("ad_creation_time") or retrieved_at,
                "delivery_start": ad.get("ad_delivery_start_time"),
                "delivery_stop": ad.get("ad_delivery_stop_time"),
                "platforms": json.dumps(ad.get("publisher_platforms") or []),
                "source": "Meta Ad Library API",
                "source_url": "https://www.facebook.com/ads/library/",
                "retrieved_at": retrieved_at,
            })
    frame = pd.DataFrame(rows, columns=COLUMNS).drop_duplicates("ad_id") if rows else pd.DataFrame(columns=COLUMNS)
    processed_dir.mkdir(parents=True, exist_ok=True)
    out = processed_dir / "ads.parquet"
    frame.to_parquet(out, index=False)
    print(f"Meta: normalized {len(frame)} ads to {out}")
    return frame


if __name__ == "__main__":
    normalize_ads()
