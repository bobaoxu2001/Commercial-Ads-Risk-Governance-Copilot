from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    raw_dir: Path = ROOT / "data" / "raw"
    processed_dir: Path = ROOT / "data" / "processed"
    policy_dir: Path = ROOT / "data" / "policies"
    db_path: Path = ROOT / os.getenv("ADSHIELD_DB_PATH", "data/processed/adshield.duckdb")
    meta_access_token: str | None = os.getenv("META_ACCESS_TOKEN") or None
    meta_graph_api_version: str = os.getenv("META_GRAPH_API_VERSION", "v23.0")
    meta_ad_country: str = os.getenv("META_AD_COUNTRY", "US")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    cfpb_max_records: int = int(os.getenv("CFPB_MAX_RECORDS", "1000"))


settings = Settings()
