"""
Stage 5 — Per-affiliate justification documents via individual Gemini calls.
One call per non-pay_in_full affiliate. Saves markdown to justifications/{affiliate_id}.md
"""
import json
from datetime import date
from pathlib import Path

from utils.gemini import call_gemini

FEATURES_FILE = Path(__file__).parent.parent / "affiliate_features.json"
CLASSIFICATIONS_FILE = Path(__file__).parent.parent / "classifications.json"
SCORES_FILE = Path(__file__).parent.parent / "quality_scores.json"
PAYOUTS_FILE = Path(__file__).parent.parent / "payouts.json"
DATA_DIR = Path(__file__).parent.parent / "data"
JUSTIFICATIONS_DIR = Path(__file__).parent.parent / "justifications"

REQUIRED_SECTIONS = [
    "## Observed Signals",
    "## Statistical Evidence",
    "## Policy Clauses Referenced",
    "## Example Signup IDs Under Review",
    "## Reason for Recommendation",
    "## What Would Change This Decision",
]


def _sample_signup_ids(signups: list[dict], affiliate_id: str, n: int = 5) -> list[str]:
    return sorted(
        s["signup_id"] for s in signups if s["affiliate_id"] == affiliate_id
    )[:n]


def build_prompt(
    aff_id: str,
    feat: dict,
    classification: dict,
    score: dict,
    payout: dict,
    example_ids: list[str],
) -> str:
    today = date.today().isoformat()
    return f"""You are a compliance analyst writing a formal affiliate review document.

Write a factual, non-accusatory markdown document for affiliate {aff_id}.
Use precise language. Do not speculate beyond the data provided.

## Input Data

### Feature Vector
{json.dumps(feat, indent=2)}

### Classification
{json.dumps(classification, indent=2)}

### Quality Score
{json.dumps(score, indent=2)}

### Payout Recommendation
{json.dumps(payout, indent=2)}

### Example Signup IDs Under Review
{json.dumps(example_ids)}

## Required Output Format

Produce the document with EXACTLY these section headers in this order:

# Affiliate Review: {aff_id}
**Date:** {today}
**Recommendation:** {payout.get('recommendation')}
**Risk Level:** {payout.get('risk_level')}

## Observed Signals
[Describe the observable patterns without accusatory language]

## Statistical Evidence
[Present specific numeric values from the feature vector]

## Policy Clauses Referenced
[List each policy clause and how it applies]

## Example Signup IDs Under Review
[List the provided signup IDs]

## Reason for Recommendation
[Explain the recommendation based on the evidence]

## What Would Change This Decision
[Describe what evidence or clarification would alter the recommendation]

Respond only with the markdown document. Do not include markdown code fences, preamble, or explanation outside the document.
"""


def run(
    features_file: Path = FEATURES_FILE,
    classifications_file: Path = CLASSIFICATIONS_FILE,
    scores_file: Path = SCORES_FILE,
    payouts_file: Path = PAYOUTS_FILE,
    data_dir: Path = DATA_DIR,
    justifications_dir: Path = JUSTIFICATIONS_DIR,
) -> list[str]:
    with open(features_file) as f:
        features = json.load(f)
    with open(classifications_file) as f:
        classifications = json.load(f)
    with open(scores_file) as f:
        scores = json.load(f)
    with open(payouts_file) as f:
        payouts = json.load(f)
    with open(data_dir / "signups.json") as f:
        signups = json.load(f)

    feat_map = {x["affiliate_id"]: x for x in features}
    cls_map = {x["affiliate_id"]: x for x in classifications}
    score_map = {x["affiliate_id"]: x for x in scores}

    justifications_dir.mkdir(parents=True, exist_ok=True)
    generated = []

    for payout in payouts:
        if payout["recommendation"] == "pay_in_full":
            continue

        aff_id = payout["affiliate_id"]
        feat = feat_map[aff_id]
        cls = cls_map[aff_id]
        score = score_map[aff_id]
        example_ids = _sample_signup_ids(signups, aff_id)

        prompt = build_prompt(aff_id, feat, cls, score, payout, example_ids)

        raw = call_gemini(
            prompt=prompt,
            stage="JUSTIFICATIONS_GENERATED",
            affiliate_id=aff_id,
            input_artifacts=[
                "affiliate_features.json",
                "classifications.json",
                "quality_scores.json",
                "payouts.json",
            ],
            output_artifact=f"justifications/{aff_id}.md",
        )

        doc_path = justifications_dir / f"{aff_id}.md"
        with open(doc_path, "w") as f:
            f.write(raw)

        generated.append(aff_id)
        print(f"[s5_justifications] Generated justification for {aff_id} → {doc_path}")

    return generated
