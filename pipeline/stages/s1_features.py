"""
Stage 1 — Deterministic feature engineering. No Gemini calls.
Loads signups and trade data, computes per-affiliate feature vectors.
"""
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

DISPOSABLE_DOMAINS = {
    "tempmail.io", "guerrillamail.com", "mailinator.com", "throwam.com",
    "yopmail.com", "sharklasers.com", "trashmail.com", "fakeinbox.com",
}

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_FILE = Path(__file__).parent.parent / "affiliate_features.json"


def _ip24_prefix(ip_hash: str) -> str:
    """Extract /24 group key: everything before the last underscore+digits block."""
    parts = ip_hash.rsplit("_", 1)
    return parts[0] if len(parts) == 2 else ip_hash


def _is_disposable(email: str) -> bool:
    domain = email.split("@")[-1].lower() if "@" in email else ""
    return domain in DISPOSABLE_DOMAINS


def _parse_ts(ts_str: str) -> datetime:
    return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))


def compute_features(signups: list[dict], trades: list[dict]) -> list[dict]:
    trade_map: dict[str, dict] = {t["signup_id"]: t for t in trades}

    by_aff: dict[str, list[dict]] = defaultdict(list)
    for s in signups:
        by_aff[s["affiliate_id"]].append(s)

    results = []
    for aff_id in sorted(by_aff.keys()):
        aff_signups = by_aff[aff_id]
        total = len(aff_signups)

        # --- Identity signals ---
        fp_counts = Counter(s["device_fingerprint"] for s in aff_signups)
        reused_fps = sum(1 for s in aff_signups if fp_counts[s["device_fingerprint"]] > 1)
        fp_reuse_rate = reused_fps / total if total else 0.0

        ip24_counts = Counter(_ip24_prefix(s["ip_hash"]) for s in aff_signups)
        top_ip24, top_ip24_count = ip24_counts.most_common(1)[0] if ip24_counts else ("", 0)
        ip24_concentration = top_ip24_count / total if total else 0.0

        disposable_count = sum(1 for s in aff_signups if _is_disposable(s["email"]))
        disposable_rate = disposable_count / total if total else 0.0

        country_counts = Counter(s["country"] for s in aff_signups)
        top_country, top_country_count = country_counts.most_common(1)[0] if country_counts else ("", 0)
        country_concentration = top_country_count / total if total else 0.0

        utm_counts = Counter(s["utm_source"] for s in aff_signups)
        top_utm, _ = utm_counts.most_common(1)[0] if utm_counts else ("", 0)
        utm_concentration = utm_counts[top_utm] / total if total else 0.0

        # --- Velocity ---
        timestamps = sorted(_parse_ts(s["timestamp"]) for s in aff_signups)
        # bucket by minute
        minute_buckets: Counter = Counter()
        peak_minute_window = ""
        for ts in timestamps:
            minute_key = ts.strftime("%Y-%m-%dT%H:%M")
            minute_buckets[minute_key] += 1
        if minute_buckets:
            peak_minute_window, peak_minute_count = minute_buckets.most_common(1)[0]
            peak_per_minute = peak_minute_count / 1.0
        else:
            peak_minute_window, peak_minute_count, peak_per_minute = "", 0, 0.0

        # --- Trading & deposit quality ---
        with_trades = [s for s in aff_signups if s["signup_id"] in trade_map]
        n_with_trades = len(with_trades)

        first_deposits = [trade_map[s["signup_id"]]["first_deposit_usd"] for s in with_trades]
        total_deposits_list = [trade_map[s["signup_id"]]["total_deposits_usd"] for s in with_trades]
        total_withdrawals_list = [trade_map[s["signup_id"]]["total_withdrawals_usd"] for s in with_trades]
        trades_counts = [trade_map[s["signup_id"]]["trades_count"] for s in with_trades]
        active_days_list = [trade_map[s["signup_id"]]["first_30d_active_days"] for s in with_trades]

        avg_first_deposit = sum(first_deposits) / n_with_trades if n_with_trades else 0.0
        avg_total_deposits = sum(total_deposits_list) / n_with_trades if n_with_trades else 0.0
        avg_trades = sum(trades_counts) / n_with_trades if n_with_trades else 0.0
        avg_active_days = sum(active_days_list) / n_with_trades if n_with_trades else 0.0

        retention_count = sum(
            1 for i, s in enumerate(with_trades)
            if total_deposits_list[i] > first_deposits[i]
        )
        deposit_retention_rate = retention_count / n_with_trades if n_with_trades else 0.0

        total_withdrawals_usd = sum(total_withdrawals_list)
        total_deposits_usd = sum(total_deposits_list)
        withdrawal_rate = total_withdrawals_usd / total_deposits_usd if total_deposits_usd > 0 else 0.0

        dormant_count = sum(
            1 for s in with_trades
            if trade_map[s["signup_id"]]["trades_count"] == 0
            and trade_map[s["signup_id"]]["first_deposit_usd"] == 0.0
        )
        dormant_rate = dormant_count / n_with_trades if n_with_trades else 0.0

        results.append({
            "affiliate_id": aff_id,
            "signup_count": total,
            "device_fingerprint_reuse_rate": round(fp_reuse_rate, 4),
            "device_fingerprint_reuse_count": reused_fps,
            "ip_24_concentration": round(ip24_concentration, 4),
            "ip_24_top_block": top_ip24,
            "ip_24_top_block_count": top_ip24_count,
            "disposable_email_rate": round(disposable_rate, 4),
            "disposable_email_count": disposable_count,
            "country_concentration": round(country_concentration, 4),
            "top_country": top_country,
            "top_country_count": top_country_count,
            "utm_source_concentration": round(utm_concentration, 4),
            "top_utm_source": top_utm,
            "peak_signups_per_minute": float(peak_per_minute),
            "peak_minute_window": peak_minute_window,
            "peak_minute_count": peak_minute_count,
            "avg_first_deposit_usd": round(avg_first_deposit, 2),
            "avg_total_deposits_usd": round(avg_total_deposits, 2),
            "avg_trades_count": round(avg_trades, 2),
            "avg_first_30d_active_days": round(avg_active_days, 2),
            "deposit_retention_rate": round(deposit_retention_rate, 4),
            "deposit_retention_count": retention_count,
            "withdrawal_rate": round(withdrawal_rate, 4),
            "total_withdrawals_usd": round(total_withdrawals_usd, 2),
            "total_deposits_usd": round(total_deposits_usd, 2),
            "dormant_account_rate": round(dormant_rate, 4),
            "dormant_account_count": dormant_count,
            "total_signups_with_trade_data": n_with_trades,
            "total_signups": total,
        })

    return results


def run(data_dir: Path = DATA_DIR, output_file: Path = OUTPUT_FILE) -> list[dict]:
    with open(data_dir / "signups.json") as f:
        signups = json.load(f)
    with open(data_dir / "deposit_and_trade_summary.json") as f:
        trades = json.load(f)

    features = compute_features(signups, trades)

    with open(output_file, "w") as f:
        json.dump(features, f, indent=2)

    print(f"[s1_features] Computed features for {len(features)} affiliates → {output_file}")
    return features
