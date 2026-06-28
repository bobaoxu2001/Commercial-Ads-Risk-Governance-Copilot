# Evaluation Report

Generated: 2026-06-28T12:46:27.011591+00:00

This report is calculated from the current local DuckDB mart. It never substitutes fabricated labels. Precision, recall, and F1 remain unavailable until human review feedback exists.

## Current deterministic workflow

- **Status:** available
- **Scored Cases:** 956
- **Escalation Rate:** 0.997
- **Auto Decision Coverage:** 0.003
- **Evidence Extraction Completeness:** 0.871
- **Estimated Review Minutes Saved:** 9
- **Labeled Cases:** 0
- **Precision:** None
- **Recall:** None
- **F1:** None
- **Label Note:** Precision/recall/F1 appear only after reviewer labels exist.

## Rule vs. LLM comparison

The deterministic rules engine (`deterministic_rules_v1`) is the default and is evaluated for every case. If `OPENAI_API_KEY` is configured, `src/risk/comparison.py` produces a second structured assessment for a 5-case sample through the optional `src/risk/llm_evaluator.py`; no paid call is made by default. The same data also powers the dashboard's `/api/llm-comparison` panel.

No OPENAI_API_KEY is configured, so no LLM call is made. Deterministic rule-based scoring remains the default for every case; LLM comparison is an optional, opt-in layer.

Sampled deterministic decisions (the authoritative default). The LLM column is intentionally
empty because no `OPENAI_API_KEY` is configured — nothing is fabricated.

| Case | Source | Rule category | Severity | Rule action | LLM (optional) |
|---|---|---|---|---|---|
| cfpb-3954356 | CFPB | Financial Scam / High-Risk Financial Services | critical | hard reject | not run (no key) |
| cfpb-16303317 | CFPB | Financial Scam / High-Risk Financial Services | high | soft reject | not run (no key) |
| cfpb-2866962 | CFPB | Financial Scam / High-Risk Financial Services | high | soft reject | not run (no key) |
| cfpb-10134115 | CFPB | Financial Scam / High-Risk Financial Services | high | escalate to human review | not run (no key) |
| cfpb-1251200 | CFPB | Financial Scam / High-Risk Financial Services | high | escalate to human review | not run (no key) |

## Interpretation limits

CFPB complaints are not verified examples of policy-violating ads, and FTC rows are aggregates. These sources provide consumer-harm priors and vocabulary, not ground-truth ad enforcement labels. Human review remains required for ambiguous decisions.
