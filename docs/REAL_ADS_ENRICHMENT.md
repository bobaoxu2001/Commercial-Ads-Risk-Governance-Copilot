# Real Ads Enrichment (Meta Ad Library)

AdShield AI is built around **real public data**. By default it runs on public FTC and CFPB risk
cases. When official Meta Ad Library credentials are supplied, it additionally ingests **real ad
creatives** so the queue contains genuine commercial ad text alongside the consumer-harm priors.

This document explains exactly how that enrichment works, what is queried, where files land, how many
records the current run retrieved, and — importantly — what happens honestly when no token is present.

## What the default (no-token) demo uses

| Mode | Data in the dashboard | Requires |
|---|---|---|
| **Default demo** | Public **FTC** fraud aggregates + **CFPB** consumer complaints, scored as risk *priors* | No keys |
| **+ Meta enrichment** | Above **plus real ad creatives** from the official Meta Ad Library API | `META_ACCESS_TOKEN` |

The default demo is fully functional with **no credentials**: ingestion, normalization, evidence
extraction, scoring, policy retrieval, analytics, feedback, and the full dashboard all run on real
public FTC/CFPB records. Meta enrichment only adds a second, complementary kind of real data — actual
ad creative examples — when a token is available.

## How enrichment works when `META_ACCESS_TOKEN` is provided

Implemented in [`src/ingest/fetch_meta_ads.py`](../src/ingest/fetch_meta_ads.py):

1. The fetcher reads `META_ACCESS_TOKEN`, `META_GRAPH_API_VERSION` (default `v23.0`), and
   `META_AD_COUNTRY` (default `US`) from the environment.
2. For each keyword it calls the official endpoint
   `https://graph.facebook.com/<version>/ads_archive` with `ad_type=ALL`, `limit=100`, and the
   country in `ad_reached_countries`.
3. It requests only public creative fields:
   `id, ad_creation_time, ad_creative_bodies, ad_creative_link_captions,
   ad_creative_link_descriptions, ad_creative_link_titles, page_id, page_name,
   publisher_platforms, ad_delivery_start_time, ad_delivery_stop_time`.
4. Each raw JSON response is written verbatim to disk, and a manifest records the run.
5. [`src/transform/normalize_ads.py`](../src/transform/normalize_ads.py) reads only the `data`
   arrays from those responses, concatenates the creative text fields, drops empty/duplicate ads, and
   writes the normalized `ads` table. Each ad becomes a case with id `meta-<ad_id>` and
   `source = "Meta Ad Library API"`.

The normalized ads are then scored by the same deterministic engine as every other case (see
[`RISK_SCORING_METHODOLOGY.md`](RISK_SCORING_METHODOLOGY.md)) with a lower source prior, because a
general commercial ad is not pre-filtered for risk the way a CFPB complaint is.

## Which keywords are queried

The keyword list lives in `KEYWORDS` in [`src/ingest/fetch_meta_ads.py`](../src/ingest/fetch_meta_ads.py):

```
financial scam, loan, investment, crypto, weight loss, supplement, pharmacy,
immigration, job offer, gambling, AI tool, miracle cure, debt relief, credit repair
```

These mirror the risk taxonomy (financial scams, health/weight-loss, gambling, deceptive offers) so
the retrieved creatives are relevant to the categories the engine triages.

## Where raw files are stored

```
data/raw/meta_ads/<UTC timestamp>/
    manifest.json          # run metadata (status, record count, keywords, country, endpoint)
    financial_scam.json    # one raw API response per keyword (spaces → underscores)
    loan.json
    investment.json
    ...
```

- Each run gets its own timestamped folder, so runs are reproducible and never overwrite history.
- Normalized output is written to `data/processed/ads.parquet` and loaded into the DuckDB `ads` table.
- Both `data/raw/` and `data/processed/` are **Git-ignored** — they can be reproduced and may contain
  public ad text, so they are kept local.

## How many records the current run retrieved

The repository's most recent ingestion ran **without** a `META_ACCESS_TOKEN`. The current manifest at
`data/raw/meta_ads/<timestamp>/manifest.json` reads:

```json
{
  "source": "Meta Ad Library API",
  "status": "skipped_no_token",
  "records": 0,
  "note": "Set META_ACCESS_TOKEN to enable official API enrichment; no fallback ads are fabricated."
}
```

So the current run retrieved **0 real ad records**, and `data/processed/ads.parquet` contains **0
rows**. The dashboard therefore shows the Meta source as *optional* and runs entirely on FTC/CFPB
data. To populate real creatives, set a token and re-run `make ingest && make transform`.

## What happens honestly when no token is provided

This is a deliberate truth-boundary decision:

- The fetcher writes a transparent `skipped_no_token` manifest with `records: 0` and **continues**.
  The pipeline does not fail.
- `normalize_ads()` produces an **empty `ads` table with the full schema** — it never invents
  placeholder advertisers, fake creatives, or synthetic ad text. (This is covered by
  `tests/test_normalize_ads.py`.)
- The dashboard's Command Center marks the Meta source as `optional` rather than `loaded`, and
  surfaces the real record count (0).
- The `README` and the data-limitations section state plainly that without Meta credentials the app
  has complaint-derived cases rather than real ad creatives — and says so in the UI.

No fabricated or scraped ad data is ever substituted. The only synthetic text in the project lives in
`tests/fixtures/` (all ids prefixed `test-`) and is used exclusively by the test suite.

## Reproducing enrichment

```bash
cp .env.example .env
# set META_ACCESS_TOKEN=... (and optionally META_AD_COUNTRY, META_GRAPH_API_VERSION)
make ingest      # fetch_meta_ads writes timestamped raw responses
make transform   # normalize_ads → ads.parquet → DuckDB
```

After this, the manifest `status` becomes `complete`, `records` reflects the real count returned by
the API, and the retrieved creatives appear as scored cases in the Review Queue.

## Related docs

- [Risk Scoring Methodology](RISK_SCORING_METHODOLOGY.md) — how each ad is scored once ingested.
- [Evaluation Report](EVALUATION_REPORT.md) — current metrics and rule-vs-LLM comparison.
