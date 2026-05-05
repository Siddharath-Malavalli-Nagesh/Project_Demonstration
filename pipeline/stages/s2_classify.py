"""
Stage 2 — Affiliate pattern classification via a single Gemini call.
Validates all returned classifications against controlled vocabularies.
"""
import json
from pathlib import Path

from utils.gemini import call_gemini, parse_json_response
from utils.vocab import validate_vocab

DATA_DIR = Path(__file__).parent.parent / "data"
FEATURES_FILE = Path(__file__).parent.parent / "affiliate_features.json"
OUTPUT_FILE = Path(__file__).parent.parent / "classifications.json"

CLASSIFICATION_DEFINITIONS = """
clean             — No suspicious signals; organic traffic pattern
sloppy            — Low quality but not clearly manufactured
synthetic_signups — Clear indicators of bulk manufactured accounts
account_farming   — Real-looking accounts but operated as a batch
incentive_abuse   — Signup pattern consistent with bonus/reward abuse
inconclusive      — Mixed signals; insufficient evidence to classify
"""


def _sample_signups(signups: list[dict], affiliate_id: str, n: int = 10) -> list[dict]:
    aff = sorted(
        [s for s in signups if s["affiliate_id"] == affiliate_id],
        key=lambda s: s["signup_id"],
    )
    return aff[:n]


def build_prompt(features: list[dict], signups: list[dict]) -> str:
    blocks = []
    for feat in features:
        aff_id = feat["affiliate_id"]
        samples = _sample_signups(signups, aff_id)
        block = {
            "affiliate_id": aff_id,
            "features": feat,
            "representative_signups": samples,
        }
        blocks.append(block)

    return f"""You are a fraud analyst classifying affiliate traffic quality.

## Classification Vocabulary
{CLASSIFICATION_DEFINITIONS}

## Affiliate Data
{json.dumps(blocks, indent=2)}

## Instructions
Analyse each affiliate's feature vector and representative signup records.
Classify each affiliate using ONLY the vocabulary values listed above.
For each triggering_feature, include the exact numeric value from the features.

Respond only with valid JSON. Do not include markdown code fences, preamble, or explanation outside the JSON.

Return a JSON array with one object per affiliate in this exact structure:
[
  {{
    "affiliate_id": "aff_001",
    "classification": "<one of the vocabulary values>",
    "confidence": "<low | medium | high>",
    "triggering_features": [
      {{
        "feature": "<feature name>",
        "value": <numeric value>,
        "why_it_matters": "<explanation>"
      }}
    ],
    "example_signup_ids": ["<signup_id>", ...],
    "explanation": "<concise explanation>"
  }}
]
"""


def run(
    features_file: Path = FEATURES_FILE,
    data_dir: Path = DATA_DIR,
    output_file: Path = OUTPUT_FILE,
) -> list[dict]:
    with open(features_file) as f:
        features = json.load(f)
    with open(data_dir / "signups.json") as f:
        signups = json.load(f)

    prompt = build_prompt(features, signups)

    raw = call_gemini(
        prompt=prompt,
        stage="PATTERNS_CLASSIFIED",
        affiliate_id=None,
        input_artifacts=["affiliate_features.json", "signups.json"],
        output_artifact="classifications.json",
    )

    classifications = parse_json_response(raw, "PATTERNS_CLASSIFIED")

    if not isinstance(classifications, list):
        raise ValueError("Expected a JSON array from classification stage")

    for record in classifications:
        validate_vocab(record["classification"], "SUSPICION_CLASSIFICATIONS")
        validate_vocab(record["confidence"], "CONFIDENCE_LEVELS")
        if not record.get("triggering_features"):
            raise ValueError(f"No triggering_features for {record['affiliate_id']}")
        for tf in record["triggering_features"]:
            if not isinstance(tf.get("value"), (int, float)):
                raise ValueError(
                    f"triggering_feature value must be numeric for {record['affiliate_id']}: {tf}"
                )
        if not record.get("example_signup_ids"):
            raise ValueError(f"No example_signup_ids for {record['affiliate_id']}")

    with open(output_file, "w") as f:
        json.dump(classifications, f, indent=2)

    print(f"[s2_classify] Classified {len(classifications)} affiliates → {output_file}")
    return classifications
