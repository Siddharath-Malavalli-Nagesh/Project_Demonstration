"""
Stage 8 — Affiliate-facing communications via Gemini.
One call per non-pay_in_full affiliate. Outputs concatenated markdown.
"""
import json
from pathlib import Path

from utils.gemini import call_gemini

FEATURES_FILE = Path(__file__).parent.parent / "affiliate_features.json"
PAYOUTS_FILE = Path(__file__).parent.parent / "payouts.json"
CLASSIFICATIONS_FILE = Path(__file__).parent.parent / "classifications.json"
OUTPUT_FILE = Path(__file__).parent.parent / "affiliate_communications.md"

BANNED_WORDS = {"fraud", "suspicious", "fake", "manufactured", "bot", "scam"}


def build_prompt(aff_id: str, feat: dict, classification: dict, payout: dict) -> str:
    return f"""You are a client relations manager drafting a professional email to an affiliate partner.

## Instructions
Write a professional, collaborative email to affiliate {aff_id}.
The email must:
1. Open by noting this is part of a routine periodic quality review — NOT an accusation
2. Reference 2–3 specific data signals carefully using neutral language
   (e.g. "we observed elevated account dormancy" NOT "fake accounts")
3. Explain the review process and the expected timeline ({14} business days)
4. List exactly what information or clarification is needed from the affiliate
5. Close with a collaborative, non-threatening tone

BANNED WORDS — never use any of these: fraud, suspicious, fake, manufactured, bot, scam

## Affiliate Context
- Affiliate ID: {aff_id}
- Quality Score: {payout.get('quality_score', 'N/A')} (not mentioned in email)
- Recommendation: {payout['recommendation']} (not mentioned in email — frame as "review")
- Risk Level: {payout['risk_level']} (internal only — do not mention)

### Observable Signals (select 2–3 for the email)
- Signup count: {feat['signup_count']}
- Dormant account rate: {feat['dormant_account_rate']:.1%}
- Disposable email rate: {feat['disposable_email_rate']:.1%}
- Device fingerprint reuse rate: {feat['device_fingerprint_reuse_rate']:.1%}
- Average first deposit: ${feat['avg_first_deposit_usd']:.2f}
- Average active days (first 30d): {feat['avg_first_30d_active_days']:.1f}
- Withdrawal rate: {feat['withdrawal_rate']:.1%}

Respond only with the email text. Do not include markdown code fences, preamble, or explanation outside the email.
"""


def _check_banned_words(text: str) -> list[str]:
    lower = text.lower()
    return [w for w in BANNED_WORDS if w in lower]


def run(
    features_file: Path = FEATURES_FILE,
    payouts_file: Path = PAYOUTS_FILE,
    classifications_file: Path = CLASSIFICATIONS_FILE,
    output_file: Path = OUTPUT_FILE,
) -> list[str]:
    with open(features_file) as f:
        features = json.load(f)
    with open(payouts_file) as f:
        payouts = json.load(f)
    with open(classifications_file) as f:
        classifications = json.load(f)

    feat_map = {x["affiliate_id"]: x for x in features}
    cls_map = {x["affiliate_id"]: x for x in classifications}

    non_full = [p for p in payouts if p["recommendation"] != "pay_in_full"]

    sections = []
    generated = []

    for payout in non_full:
        aff_id = payout["affiliate_id"]
        feat = feat_map[aff_id]
        cls = cls_map[aff_id]

        prompt = build_prompt(aff_id, feat, cls, payout)
        raw = call_gemini(
            prompt=prompt,
            stage="COMMUNICATIONS_DRAFTED",
            affiliate_id=aff_id,
            input_artifacts=["affiliate_features.json", "payouts.json", "classifications.json"],
            output_artifact="affiliate_communications.md",
        )

        found_banned = _check_banned_words(raw)
        if found_banned:
            print(f"  [s8_comms] Warning: banned words found in {aff_id} communication: {found_banned}")

        sections.append(f"# Communication: {aff_id}\n\n{raw.strip()}")
        generated.append(aff_id)
        print(f"[s8_comms] Drafted communication for {aff_id}")

    with open(output_file, "w") as f:
        f.write("\n\n---\n\n".join(sections))

    print(f"[s8_comms] Saved {len(generated)} communications → {output_file}")
    return generated
