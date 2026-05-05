"""
Stage 7 — Deterministic 90-day LTV forecast. No Gemini calls.
Uses retention-adjusted deposit projection method.
"""
import json
from pathlib import Path

FEATURES_FILE = Path(__file__).parent.parent / "affiliate_features.json"
OUTPUT_FILE = Path(__file__).parent.parent / "ltv_forecast.json"

METHOD = "retention_adjusted_deposit_projection_v1"
KEY_ASSUMPTIONS = [
    "Dormant rate remains stable",
    "Deposit behaviour observed in first 30 days is representative",
    "Withdrawal rate is constant",
]
CI_FACTOR_LOW = 0.70
CI_FACTOR_HIGH = 1.30


def forecast_affiliate(feat: dict) -> dict:
    signup_count = feat["signup_count"]
    dormant_rate = feat["dormant_account_rate"]
    deposit_retention_rate = feat["deposit_retention_rate"]
    avg_total_deposits = feat["avg_total_deposits_usd"]
    withdrawal_rate = feat["withdrawal_rate"]

    projected_active_users = signup_count * (1 - dormant_rate) * deposit_retention_rate
    avg_monthly_deposit = avg_total_deposits  # observed in ~30d window
    projected_90d_deposit = projected_active_users * avg_monthly_deposit * 3
    withdrawal_adjustment = projected_90d_deposit * (1 - withdrawal_rate)
    ltv_forecast = withdrawal_adjustment

    lower = round(ltv_forecast * CI_FACTOR_LOW, 2)
    upper = round(ltv_forecast * CI_FACTOR_HIGH, 2)

    return {
        "affiliate_id": feat["affiliate_id"],
        "forecast_90d_ltv_usd": round(ltv_forecast, 2),
        "confidence_interval": [lower, upper],
        "method": METHOD,
        "key_assumptions": KEY_ASSUMPTIONS,
    }


def run(
    features_file: Path = FEATURES_FILE,
    output_file: Path = OUTPUT_FILE,
) -> list[dict]:
    with open(features_file) as f:
        features = json.load(f)

    forecasts = [forecast_affiliate(feat) for feat in features]

    with open(output_file, "w") as f:
        json.dump(forecasts, f, indent=2)

    print(f"[s7_ltv] Forecasted LTV for {len(forecasts)} affiliates → {output_file}")
    return forecasts
