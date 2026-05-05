"""
Stage 9 — Detection rule codification. No Gemini calls.
Generates pandas and SQL implementations for each observed pattern.
"""
import json
from pathlib import Path

CLASSIFICATIONS_FILE = Path(__file__).parent.parent / "classifications.json"
FEATURES_FILE = Path(__file__).parent.parent / "affiliate_features.json"
OUTPUT_FILE = Path(__file__).parent.parent / "detection_rules.md"

RULES = [
    {
        "name": "burst_signup_velocity",
        "description": "Detects affiliates with abnormally high signup rates within a single minute.",
        "trigger": "peak_signups_per_minute > 5",
        "threshold_field": "peak_signups_per_minute",
        "threshold_value": 5,
        "operator": ">",
        "pandas": "df[df['peak_signups_per_minute'] > 5]",
        "sql": (
            "SELECT affiliate_id, peak_signups_per_minute\n"
            "FROM affiliate_features\n"
            "WHERE peak_signups_per_minute > 5;"
        ),
    },
    {
        "name": "device_fingerprint_cluster",
        "description": "Detects affiliates where a high proportion of signups share device fingerprints.",
        "trigger": "device_fingerprint_reuse_rate > 0.4",
        "threshold_field": "device_fingerprint_reuse_rate",
        "threshold_value": 0.4,
        "operator": ">",
        "pandas": "df[df['device_fingerprint_reuse_rate'] > 0.4]",
        "sql": (
            "SELECT affiliate_id, device_fingerprint_reuse_rate\n"
            "FROM affiliate_features\n"
            "WHERE device_fingerprint_reuse_rate > 0.4;"
        ),
    },
    {
        "name": "ip_block_concentration",
        "description": "Detects affiliates where signups cluster within a single IP /24 block.",
        "trigger": "ip_24_concentration > 0.6",
        "threshold_field": "ip_24_concentration",
        "threshold_value": 0.6,
        "operator": ">",
        "pandas": "df[df['ip_24_concentration'] > 0.6]",
        "sql": (
            "SELECT affiliate_id, ip_24_concentration, ip_24_top_block\n"
            "FROM affiliate_features\n"
            "WHERE ip_24_concentration > 0.6;"
        ),
    },
    {
        "name": "disposable_email_cluster",
        "description": "Detects affiliates with a high rate of disposable or temporary email domains.",
        "trigger": "disposable_email_rate > 0.3",
        "threshold_field": "disposable_email_rate",
        "threshold_value": 0.3,
        "operator": ">",
        "pandas": "df[df['disposable_email_rate'] > 0.3]",
        "sql": (
            "SELECT affiliate_id, disposable_email_rate, disposable_email_count\n"
            "FROM affiliate_features\n"
            "WHERE disposable_email_rate > 0.3;"
        ),
    },
    {
        "name": "mass_dormancy",
        "description": "Detects affiliates where the majority of referred accounts never traded.",
        "trigger": "dormant_account_rate > 0.6",
        "threshold_field": "dormant_account_rate",
        "threshold_value": 0.6,
        "operator": ">",
        "pandas": "df[df['dormant_account_rate'] > 0.6]",
        "sql": (
            "SELECT affiliate_id, dormant_account_rate, dormant_account_count\n"
            "FROM affiliate_features\n"
            "WHERE dormant_account_rate > 0.6;"
        ),
    },
    {
        "name": "high_withdrawal_ratio",
        "description": "Detects affiliates where referred users withdraw most of their deposited funds.",
        "trigger": "withdrawal_rate > 0.7",
        "threshold_field": "withdrawal_rate",
        "threshold_value": 0.7,
        "operator": ">",
        "pandas": "df[df['withdrawal_rate'] > 0.7]",
        "sql": (
            "SELECT affiliate_id, withdrawal_rate, total_withdrawals_usd, total_deposits_usd\n"
            "FROM affiliate_features\n"
            "WHERE withdrawal_rate > 0.7;"
        ),
    },
]


def _build_doc(rules: list[dict], classifications: list[dict], features: list[dict]) -> str:
    cls_map = {c["affiliate_id"]: c["classification"] for c in classifications}
    feat_map = {f["affiliate_id"]: f for f in features}

    lines = [
        "# Detection Rules\n",
        "Rules are programmatically generated from computed features and classification results.",
        "Each rule includes the trigger condition, affected affiliates, and both pandas and SQL implementations.\n",
        "---\n",
    ]

    for rule in rules:
        field = rule["threshold_field"]
        threshold = rule["threshold_value"]
        op = rule["operator"]

        # Find which affiliates currently trigger this rule
        triggered = []
        for feat in features:
            val = feat.get(field, 0)
            if op == ">" and val > threshold:
                triggered.append(f"{feat['affiliate_id']} ({field}={val:.4f}, cls={cls_map.get(feat['affiliate_id'], 'unknown')})")
            elif op == ">=" and val >= threshold:
                triggered.append(f"{feat['affiliate_id']} ({field}={val:.4f}, cls={cls_map.get(feat['affiliate_id'], 'unknown')})")

        lines.append(f"## Rule: `{rule['name']}`\n")
        lines.append(f"**Description:** {rule['description']}\n")
        lines.append(f"**Trigger:** `{rule['trigger']}`\n")
        lines.append(f"**Currently Triggered By:** {', '.join(triggered) if triggered else 'None'}\n")
        lines.append("### Pandas Implementation\n")
        lines.append("```python")
        lines.append("import pandas as pd")
        lines.append("")
        lines.append("# df is a DataFrame loaded from affiliate_features.json")
        lines.append(f"flagged = {rule['pandas']}")
        lines.append("```\n")
        lines.append("### SQL Implementation\n")
        lines.append("```sql")
        lines.append(rule["sql"])
        lines.append("```\n")
        lines.append("---\n")

    return "\n".join(lines)


def run(
    classifications_file: Path = CLASSIFICATIONS_FILE,
    features_file: Path = FEATURES_FILE,
    output_file: Path = OUTPUT_FILE,
) -> list[dict]:
    with open(classifications_file) as f:
        classifications = json.load(f)
    with open(features_file) as f:
        features = json.load(f)

    doc = _build_doc(RULES, classifications, features)

    with open(output_file, "w") as f:
        f.write(doc)

    print(f"[s9_rules] Generated {len(RULES)} detection rules → {output_file}")
    return RULES
