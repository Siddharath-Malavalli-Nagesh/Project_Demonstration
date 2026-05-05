# Deriv Technical Test
# Affiliate Pipeline: Build Specification & Checklist

---
## Setup guidelines
Step 1 — Install dependencies

python -m venv venv
source ./venv/bin/activate
cd /Users/siddharath-malavalli-nagesh/Project_Demonstration/pipeline
pip install -r requirements.txt
Step 2 — Run the full pipeline


python main.py
Step 3 — Run the validator to check all outputs


python validate.py


## Overview

A replayable, audit-ready pipeline that ingests anonymised affiliate signup and trading data, computes deterministic quality features, classifies affiliate cohorts, scores quality, recommends payouts, and produces justification documents. The pipeline must be fully regenerable — static precomputed outputs are not acceptable.

---

## Input Files

| File | Description |
|---|---|
| `signups.json` | Affiliate-driven signup records |
| `deposit_and_trade_summary.json` | Per-signup deposit and trading activity |
| `payout_policy.json` | CPA payout rules, thresholds, and action vocabulary |

**Scale requirement:** ~500 signups across 6 affiliate IDs with matching deposit/trade summaries for all signups.

---

## Controlled Vocabularies

These must be defined in code and all LLM outputs validated against them.

**Suspicion Classifications**
`clean` · `sloppy` · `synthetic_signups` · `account_farming` · `incentive_abuse` · `inconclusive`

**Payout Recommendations**
`pay_in_full` · `pay_partial` · `hold_pending_review` · `clawback`

**Risk Levels**
`low` · `medium` · `high` · `critical`

---

## Seed Data Patterns

| Affiliate | Required Pattern |
|---|---|
| `aff_001` | Signup-burst: repeated device fingerprint, sequential timestamps, disposable email domains |
| `aff_002` | High quality: varied fingerprints, real email domains, geographic diversity, strong deposits |
| `aff_003` | Account-farming: unique fingerprints but repeated user-agent / same IP-block proxy signal |
| `aff_004–006` | Realistic mid-quality variety |

> If evaluator-provided data uses different affiliate IDs, the pipeline must operate generically over whatever affiliates are present.

---

## Pipeline Stages

Stages must be enforced in code in this exact order. Payout recommendations must not be produced before features, classifications, and quality scores are complete.

```
INIT
 → INPUTS_LOADED
 → DATASET_EXTENDED_OR_VALIDATED
 → FEATURES_COMPUTED
 → PATTERNS_CLASSIFIED
 → QUALITY_SCORES_COMPUTED
 → PAYOUTS_RECOMMENDED
 → JUSTIFICATIONS_GENERATED
 → OPTIONAL_REVIEWS_GENERATED
 → VALIDATION_COMPLETE
 → RESULTS_FINALISED
```

---

## Stage Details

### Stage 1 — Quality Feature Engineering *(Must Complete)*

Computed entirely in deterministic code — no LLM involvement. Output saved to `affiliate_features.json`. Every record must include supporting counts and denominators for auditability.

**Features to compute per affiliate:**

| Feature | Description |
|---|---|
| Signup velocity | Peak signups per minute |
| Device fingerprint reuse rate | Ratio of reused fingerprints |
| IP `/24` concentration | Cluster concentration of IP addresses |
| Disposable email domain rate | Share of signups using throwaway domains |
| Avg first-30d active days | Mean active days in first 30 days |
| Deposit retention | % of signups with a second deposit or total > first deposit |
| Withdrawal rate | Withdrawals relative to deposits |
| Avg first deposit (USD) | Mean first deposit amount |
| Avg total deposits (USD) | Mean cumulative deposit amount |
| Avg trades count | Mean number of trades |
| Dormant account rate | Share of accounts dormant at 30 days |
| Country concentration | Geographic clustering of signups |
| UTM source concentration | Channel clustering of signups |

---

### Stage 2 — Suspicion Pattern Classification *(Must Complete)*

One combined LLM call using feature vectors, 10 representative signups per affiliate, controlled vocabulary, and classification definitions.

**Output schema per affiliate (`classifications.json`):**

```json
{
  "affiliate_id": "string",
  "classification": "synthetic_signups",
  "confidence": "low | medium | high",
  "triggering_features": [
    {
      "feature": "device_fingerprint_reuse_rate",
      "value": 0.82,
      "why_it_matters": "string"
    }
  ],
  "example_signup_ids": ["s001", "s002"],
  "explanation": "string"
}
```

> For the public seed fixture: `aff_001` → `synthetic_signups`, `aff_003` → `account_farming`

---

### Stage 3 — Deterministic Quality Score *(Must Complete)*

Computed entirely in deterministic code. Formula and weights documented in `quality_score_model.md`. Output saved to `quality_scores.json`. Scores must be identical across repeated runs with the same inputs.

**Formula inputs:**

- Suspicious classification penalty
- Signup velocity
- Device reuse rate
- IP concentration
- Disposable email rate
- Deposit retention
- Active days average
- Trades count average
- Dormant rate
- Withdrawal behaviour

**Output schema per affiliate:**

```json
{
  "affiliate_id": "string",
  "quality_score": 0,
  "risk_level": "high",
  "formula_version": "string",
  "positive_factors": ["string"],
  "negative_factors": ["string"]
}
```

---

### Stage 4 — Payout Recommendation *(Must Complete)*

One combined LLM call using features, classifications, quality scores, payout policy, and representative evidence. Output saved to `payouts.json`.

**Output schema per affiliate:**

```json
{
  "affiliate_id": "string",
  "recommendation": "hold_pending_review",
  "pay_partial_percent": null,
  "policy_references": ["min_first_deposit_usd", "fraud_clawback_window_days"],
  "evidence_summary": "string",
  "example_signup_ids": ["s001", "s002"],
  "risk_level": "high"
}
```

> `pay_partial` recommendations must include a recommended percentage.

---

### Stage 5 — Audit Justification Documents *(Must Complete)*

One LLM call per non-`pay_in_full` affiliate. Output saved to `justifications/{affiliate_id}.md`.

**Each document must contain:**

- Observed signals
- Statistical evidence with specific numbers
- Policy clauses referenced
- Example signup IDs
- Reason for payout recommendation
- What additional evidence would change the decision

> Tone must be factual and non-accusatory throughout.

---

### Stage 6 — Adversarial Self-Review *(Should Attempt)*

Second LLM pass arguing the affiliate's defense for every non-`pay_in_full` recommendation.

**Defense should consider:**
- Legitimate promotional burst
- Country-specific email domain norms
- Device sharing patterns
- Early-stage cohort activity lag
- Incomplete 30-day maturity window

If the defense is credible, downgrade recommendation severity in code, or record why it was not downgraded. Output saved to `adversarial_review.json`.

---

### Stage 7 — Cohort LTV Forecast *(Should Attempt)*

Deterministic code or documented statistical method. Output saved to `ltv_forecast.json`.

```json
{
  "affiliate_id": "string",
  "forecast_90d_ltv_usd": 0,
  "confidence_interval": [0, 0],
  "method": "string",
  "key_assumptions": ["string"]
}
```

---

### Stage 8 — Affiliate-Facing Communication *(Stretch)*

Non-accusatory messages for affiliates under review. Output saved to `affiliate_communications.md`.

**Each message must:**
- Request clarification, not assert wrongdoing
- Reference specific data points carefully
- Avoid fraud accusations
- Explain the review process
- State what information is needed from the affiliate

---

### Stage 9 — Detection Rule Codification *(Stretch)*

Translate detected patterns into static SQL or pandas rules for nightly execution. Output saved to `detection_rules.md`.

**Each rule must include:**
- Rule name and description
- SQL or pandas implementation
- Triggering threshold
- Expected false-positive risk
- Linked classification type

---

## LLM Call Logging

Every LLM call must be logged to `llm_calls.jsonl` — one JSON object per call.

```json
{
  "stage": "string",
  "affiliate_id": "string | null",
  "timestamp": "ISO-8601",
  "provider": "string",
  "model": "string",
  "prompt_hash": "string",
  "input_artifacts": ["path"],
  "output_artifact": "path"
}
```

**Separate log records required for:**
- Combined suspicion classification call
- Combined payout recommendation call
- Each non-`pay_in_full` audit justification call
- Adversarial self-review call (if run)
- Affiliate-facing communication call (if LLM-generated)

---

## Required Output Artifacts

| Artifact | Stage | Required? |
|---|---|---|
| `signups.json` | Input | Must |
| `deposit_and_trade_summary.json` | Input | Must |
| `payout_policy.json` | Input | Must |
| `affiliate_features.json` | Stage 1 | Must |
| `classifications.json` | Stage 2 | Must |
| `quality_scores.json` | Stage 3 | Must |
| `quality_score_model.md` | Stage 3 | Must |
| `payouts.json` | Stage 4 | Must |
| `justifications/{affiliate_id}.md` | Stage 5 | Must |
| `llm_calls.jsonl` | All stages | Must |
| `adversarial_review.json` | Stage 6 | Should |
| `ltv_forecast.json` | Stage 7 | Should |
| `affiliate_communications.md` | Stage 8 | Stretch |
| `detection_rules.md` | Stage 9 | Stretch |

---

## Technical Constraints

- Feature engineering must be deterministic code — no LLM
- Quality scoring must be deterministic code — no LLM
- Quality score formula must be documented in `quality_score_model.md`
- Suspicion classification must use only the controlled vocabulary
- Payout recommendations must reference specific policy clauses
- Affiliate-facing communication must be non-accusatory
- Do not infer protected characteristics
- Do not use country alone as evidence of suspicious activity
- Do not label affiliates as fraudulent without computed evidence
- Use anonymised data only
- Static precomputed outputs are not acceptable — pipeline must regenerate on every run

---
---


