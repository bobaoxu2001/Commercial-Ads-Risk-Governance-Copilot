# Risk Scoring Methodology & Model Card

This document describes how AdShield AI assigns a risk score and a recommended action to each
public-source case. It is the "model card" for the deterministic triage engine
(`deterministic_rules_v1`, implemented in [`src/risk/scoring.py`](../src/risk/scoring.py)).

> **Truth boundary.** This is a *triage* engine, not an enforcement model. A high score means
> "a human should look at this sooner," not "this ad violates policy." The engine is trained on no
> proprietary labels and has no access to TikTok systems or decisions.

## 1. Why deterministic rules

The triage layer is intentionally a transparent, deterministic rule engine rather than a learned
classifier:

- **Auditability.** Every score can be traced to the exact evidence terms, source, and category
  that produced it. A reviewer can reconstruct the number by hand.
- **No training labels required.** There is no ground-truth corpus of "TikTok ad violations" to
  learn from, so a supervised model would either overfit a proxy or invent labels. Rules avoid both.
- **Stability.** The same input always produces the same output, which is required for the
  evaluation, validation, and regression tests to be meaningful.
- **Reviewer trust.** Operations teams adopt a system they can reason about. The rules encode policy
  intuition that a reviewer can challenge line by line.

The optional LLM layer (see [`EVALUATION_REPORT.md`](EVALUATION_REPORT.md) and
[`src/risk/comparison.py`](../src/risk/comparison.py)) is a *second opinion* for comparison only. It
never overrides the deterministic recommendation and is not called unless `OPENAI_API_KEY` is set.

## 2. Risk score components

The score is built from a small number of named, inspectable components:

```
risk_score = min(0.98,  0.12                       # base prior (every case starts here)
                       + source_prior              # 0.22 for CFPB, 0.08 otherwise
                       + 0.115 * evidence_count)   # one term per matched signal
risk_score += 0.12      if category in {Dangerous Products, Adult / Sexualized Content}
risk_score  = min(0.98, risk_score)
```

| Component | Value | Rationale |
|---|---|---|
| Base prior | `0.12` | Floor so that even no-signal cases carry minimal review weight. |
| Source prior | `0.22` (CFPB) / `0.08` (Meta/other) | CFPB cases are consumer-harm complaints and skew toward regulated, higher-risk products; Meta creatives are general ads. |
| Evidence contribution | `0.115 × evidence_count` | Each distinct matched signal (urgency/guarantee, regulated product, off-platform contact, taxonomy keyword, landing-page mismatch) adds a fixed increment. |
| Severe-category boost | `+0.12` | Dangerous products and adult/sexualized content carry standalone harm even with few terms. |
| Cap | `0.98` | The engine never claims certainty. |

### Evidence-count contribution

Evidence is produced by [`src/risk/evidence_extractor.py`](../src/risk/evidence_extractor.py). It
extracts three operational signal groups (`urgency_or_guarantee`, `regulated_product`,
`off_platform_contact`), every matched **taxonomy** keyword, and a **landing-page mismatch** signal
when ad text and landing text have low token overlap. Each unique `(type, term)` pair counts once,
so the increment rewards breadth of corroborating signals rather than repetition of one word.
English terms match on word boundaries to avoid false hits (e.g. "secured" does not match "cure").

### Source prior

The source prior encodes *base rate*, not guilt. CFPB complaints are pre-filtered to regulated
financial products (loans, debt collection, credit reporting, money transfer), so the prior is
higher. Meta Ad Library creatives are unfiltered commercial ads, so the prior is lower and the score
relies more heavily on extracted evidence. The prior is the single most important reason the score
must not be read as a violation probability — it reflects which dataset the text came from.

## 3. Severity thresholds

Severity is a banding of the final score for queue triage:

| Severity | Condition |
|---|---|
| `critical` | `score ≥ 0.85` |
| `high` | `0.65 ≤ score < 0.85` |
| `medium` | `0.40 ≤ score < 0.65` |
| `low` | `score < 0.40` |

## 4. Confidence

Confidence reflects how much *explicit* evidence supports the score, independent of severity:

```
confidence = min(0.96, 0.5 + 0.07 * evidence_count + (0.08 if product else 0.0))
```

A case can be high-severity but low-confidence (a strong source prior with little extracted text),
which is exactly the situation that should be routed to a human rather than auto-actioned.

## 5. Recommended-action thresholds

The recommended action combines score **and** confidence so that the engine only auto-acts when both
are strong:

| Recommended action | Condition (evaluated in order) |
|---|---|
| `hard reject` | `score ≥ 0.85` **and** `confidence ≥ 0.75` |
| `soft reject` | `score ≥ 0.70` |
| `escalate to human review` | `needs_human_review` is true |
| `approve` | none of the above |

where:

```
needs_human_review = (0.40 ≤ score < 0.85) or (confidence < 0.68)
```

This means a case is sent to a human whenever it is in the ambiguous mid-band **or** the engine is
not confident — high-confidence extremes are the only cases eligible for automated routing.

### Worked examples

Reproducible from `score_case(...)` in [`src/risk/scoring.py`](../src/risk/scoring.py):

| Case | Evidence | Score | Severity | Confidence | Action |
|---|---:|---:|---|---:|---|
| Benign credit-card billing dispute (CFPB) | 1 | 0.455 | medium | 0.650 | escalate to human review |
| "Guaranteed returns, double your money, add me on WhatsApp" | 6 | 0.890 | critical | 0.960 | hard reject |
| `无视征信，黑户可贷，秒批，加微了解。` (loan) | 6 | 0.890 | critical | 0.960 | hard reject |
| `七天瘦，神药根治，100% guaranteed.` (supplement) | 8 | 0.980 | critical | 0.960 | hard reject |

The benign dispute illustrates the design intent: a regulated-product term plus the CFPB source prior
lifts the score into the medium band, but with only one signal the engine declines to auto-act and
**escalates to a human** instead.

## 6. Why this is not a final enforcement model

- It has **no access** to TikTok ads, advertiser history, account integrity signals, targeting, or
  landing-page crawls — the inputs a real enforcement decision requires.
- It scores **text only**. Real ads are multimodal (video, audio, image, overlays).
- It is tuned on **public priors**, not on labeled enforcement outcomes, so its thresholds are
  reasonable defaults, not calibrated decision boundaries.
- Market eligibility, licensing, and local law — which often decide a financial-services ad — are not
  encoded beyond a summarized policy pointer.

For these reasons the engine emits *recommendations* and routes ambiguity to people. It is a
prioritization and explanation aid, not an automated adjudicator.

## 7. False-positive / false-negative tradeoff

The thresholds are deliberately **recall-leaning** for the review queue and **precision-leaning** for
automated rejection:

- **Escalation is cheap, missed harm is expensive.** The mid-band (`0.40–0.85`) and the
  `confidence < 0.68` rule push a large share of cases to human review rather than auto-approving.
  This raises false positives *into the queue* (extra reviewer load) to reduce false negatives
  (harmful ads that slip through). On the current public sample the escalation rate is high by
  design — see [`EVALUATION_REPORT.md`](EVALUATION_REPORT.md).
- **Auto-rejection requires two independent strong signals** (high score *and* high confidence), so
  the `hard reject` path is precision-leaning: it should rarely fire on a benign case.
- **The tradeoff is tunable.** Lowering the evidence increment or raising the source prior shifts
  volume between the queue and auto-decision lanes. Because precision/recall are only computable once
  reviewers label cases, the engine never reports a precision/recall figure it cannot back with real
  feedback (the dashboard shows "Awaiting labels" until then).

## 8. Why public CFPB/FTC data are risk *priors*, not ground-truth ad violations

AdShield AI uses public FTC Consumer Sentinel aggregates and CFPB consumer complaints to learn
**vocabulary and base rates** for consumer harm — what fraudulent and high-risk offers tend to say,
which categories and markets generate the most complaints. They are used as **priors**, not labels,
because:

- **A CFPB complaint is not an adjudicated ad.** It is a consumer's report about a financial product
  or company. It is unverified, may be resolved in the company's favor, and is usually not about a
  TikTok ad at all.
- **FTC Sentinel rows are aggregates**, not individual creatives, and are explicitly described as
  unverified reports.
- **Neither dataset contains enforcement outcomes.** There is no field that says "this ad violated
  policy," so treating them as ground truth would fabricate a label that does not exist.

Using them as priors keeps the project honest: the engine borrows the *language of harm* from real
public records to triage *other* text, while every surface in the product repeats that complaints are
not confirmed violations and that human judgment owns the final call. Synthetic cases exist **only**
in `tests/fixtures/` and are prefixed `test-` so they can never enter the dashboard.

## Related docs

- [Real Ads Enrichment](REAL_ADS_ENRICHMENT.md) — how optional Meta Ad Library creatives are added.
- [Evaluation Report](EVALUATION_REPORT.md) — current metrics and rule-vs-LLM comparison.
- [Risk Taxonomy](RISK_TAXONOMY.md) — the bilingual category set.
- [Metric Dictionary](METRIC_DICTIONARY.md) — definitions and limitations for every displayed metric.
