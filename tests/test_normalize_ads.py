import json

import pandas as pd

from src.transform.normalize_ads import COLUMNS, normalize_ads


def _write_run(raw_dir, name: str, payload: dict) -> None:
    run = raw_dir / "meta_ads" / "20260101T000000Z"
    run.mkdir(parents=True, exist_ok=True)
    (run / name).write_text(json.dumps(payload), encoding="utf-8")


def test_empty_table_when_meta_token_absent(tmp_path) -> None:
    """A skipped (no-token) run yields an empty ads table and never fabricates ads."""
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    _write_run(raw_dir, "manifest.json", {"status": "skipped_no_token", "records": 0})

    frame = normalize_ads(raw_dir=raw_dir, processed_dir=processed_dir)

    assert frame.empty
    assert list(frame.columns) == COLUMNS
    saved = pd.read_parquet(processed_dir / "ads.parquet")
    assert saved.empty
    assert list(saved.columns) == COLUMNS


def test_real_ads_are_normalized_without_fabrication(tmp_path) -> None:
    """When the API returned real `data`, those exact ads are normalized — and only those."""
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    _write_run(raw_dir, "manifest.json", {"status": "complete", "records": 1})
    _write_run(raw_dir, "loan.json", {"data": [
        {"id": "123", "page_id": "p1", "page_name": "Acme", "ad_creative_bodies": ["Guaranteed loan, no credit check"]},
        {"id": "456", "page_id": "p2", "page_name": "Empty Co", "ad_creative_bodies": ["   "]},  # dropped: no text
    ]})

    frame = normalize_ads(raw_dir=raw_dir, processed_dir=processed_dir)

    assert len(frame) == 1  # the empty-text ad is dropped, not replaced by a placeholder
    row = frame.iloc[0]
    assert row["ad_id"] == "123"
    assert row["case_id"] == "meta-123"
    assert "Guaranteed loan" in row["ad_text"]
    assert row["source"] == "Meta Ad Library API"
