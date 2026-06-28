# Evaluation Report

Generated: 2026-06-28T10:29:49.813031+00:00

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

The deterministic rules engine is the default and is evaluated for every case. If `OPENAI_API_KEY` is configured, `src/risk/llm_evaluator.py` can produce a second structured assessment for sampled-case comparison; no paid call is made by default.

## Interpretation limits

CFPB complaints are not verified examples of policy-violating ads, and FTC rows are aggregates. These sources provide consumer-harm priors and vocabulary, not ground-truth ad enforcement labels. Human review remains required for ambiguous decisions.
