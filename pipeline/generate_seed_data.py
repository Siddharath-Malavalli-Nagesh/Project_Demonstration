"""
Deterministic seed data generator for the affiliate fraud detection pipeline.
Produces ~500 signups across 6 affiliates with distinct fraud patterns.
"""
import json
import random
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

SEED = 42
BASE_DATE = datetime(2025, 6, 1, 0, 0, 0, tzinfo=timezone.utc)

DISPOSABLE_DOMAINS = [
    "tempmail.io", "guerrillamail.com", "mailinator.com", "throwam.com",
    "yopmail.com", "sharklasers.com", "trashmail.com", "fakeinbox.com",
]
REAL_DOMAINS = ["gmail.com", "outlook.com", "yahoo.com", "protonmail.com", "hotmail.com"]
COUNTRIES = ["US", "GB", "DE", "FR", "CA", "AU", "NL", "SE", "BR", "ZA"]
UTM_SOURCES = ["google", "facebook", "twitter", "email", "direct", "influencer_a", "influencer_b"]


def _hash(val: str) -> str:
    return hashlib.md5(val.encode()).hexdigest()[:12]


def _fp(seed_str: str) -> str:
    return "fp_" + _hash(seed_str)


def _ip(prefix: str, host: int) -> str:
    return f"ip_{prefix}{host:02d}"


def make_signup(
    rng: random.Random,
    signup_id: str,
    affiliate_id: str,
    ts: datetime,
    email: str,
    device_fp: str,
    ip_hash: str,
    country: str,
    utm_source: str,
) -> dict:
    return {
        "signup_id": signup_id,
        "affiliate_id": affiliate_id,
        "timestamp": ts.isoformat(),
        "email": email,
        "device_fingerprint": device_fp,
        "ip_hash": ip_hash,
        "country": country,
        "utm_source": utm_source,
    }


def make_trade_summary(
    rng: random.Random,
    signup_id: str,
    affiliate_id: str,
    first_deposit: float,
    total_deposits: float,
    total_withdrawals: float,
    trades: int,
    active_days: int,
) -> dict:
    return {
        "signup_id": signup_id,
        "affiliate_id": affiliate_id,
        "first_deposit_usd": round(first_deposit, 2),
        "total_deposits_usd": round(total_deposits, 2),
        "total_withdrawals_usd": round(total_withdrawals, 2),
        "trades_count": trades,
        "first_30d_active_days": active_days,
    }


def gen_aff001(rng: random.Random, start_id: int) -> tuple[list, list]:
    """Burst signups: shared device FP, seconds apart, disposable emails, single country, single UTM."""
    signups, trades = [], []
    # 3 burst clusters
    shared_fps = [_fp(f"aff001_shared_{i}") for i in range(4)]
    base_ts = BASE_DATE + timedelta(days=2)

    for cluster in range(3):
        cluster_ts = base_ts + timedelta(hours=cluster * 6)
        for i in range(28):
            sid = f"s{start_id + cluster * 28 + i:04d}"
            ts = cluster_ts + timedelta(seconds=rng.randint(0, 90))
            domain = rng.choice(DISPOSABLE_DOMAINS)
            email = f"user{rng.randint(1000, 9999)}@{domain}"
            fp = rng.choice(shared_fps)
            ip = _ip("a0", rng.randint(1, 5))
            s = make_signup(rng, sid, "aff_001", ts, email, fp, ip, "CN", "banner_network_x")
            signups.append(s)
            first_dep = rng.uniform(10, 25) if rng.random() > 0.4 else 0.0
            total_dep = first_dep * rng.uniform(1.0, 1.1) if first_dep > 0 else 0.0
            t = make_trade_summary(rng, sid, "aff_001", first_dep, total_dep, 0.0,
                                   rng.randint(0, 3) if first_dep > 0 else 0,
                                   rng.randint(0, 2) if first_dep > 0 else 0)
            trades.append(t)

    # additional scattered signups with same FP pattern
    for i in range(24):
        sid = f"s{start_id + 84 + i:04d}"
        ts = base_ts + timedelta(days=rng.randint(0, 5), seconds=rng.randint(0, 120))
        domain = rng.choice(DISPOSABLE_DOMAINS[:4])
        email = f"usr{rng.randint(100, 999)}@{domain}"
        fp = rng.choice(shared_fps[:2])
        ip = _ip("a0", rng.randint(1, 3))
        s = make_signup(rng, sid, "aff_001", ts, email, fp, ip, "CN", "banner_network_x")
        signups.append(s)
        t = make_trade_summary(rng, sid, "aff_001", 0.0, 0.0, 0.0, 0, 0)
        trades.append(t)

    return signups, trades


def gen_aff002(rng: random.Random, start_id: int) -> tuple[list, list]:
    """High quality: unique FPs, real emails, varied countries, strong deposits."""
    signups, trades = [], []
    for i in range(90):
        sid = f"s{start_id + i:04d}"
        ts = BASE_DATE + timedelta(days=rng.randint(0, 29), hours=rng.randint(0, 23))
        domain = rng.choice(REAL_DOMAINS)
        name = f"user{rng.randint(10000, 99999)}"
        email = f"{name}@{domain}"
        fp = _fp(f"aff002_{i}_{rng.random()}")
        ip = _ip(f"b{rng.randint(10,99)}", rng.randint(1, 254))
        country = rng.choice(COUNTRIES)
        utm = rng.choice(UTM_SOURCES[:4])
        s = make_signup(rng, sid, "aff_002", ts, email, fp, ip, country, utm)
        signups.append(s)
        first_dep = rng.uniform(100, 500)
        total_dep = first_dep * rng.uniform(1.1, 2.5)
        withdrawals = total_dep * rng.uniform(0.05, 0.25)
        t = make_trade_summary(rng, sid, "aff_002", first_dep, total_dep, withdrawals,
                               rng.randint(60, 100), rng.randint(15, 25))
        trades.append(t)
    return signups, trades


def gen_aff003(rng: random.Random, start_id: int) -> tuple[list, list]:
    """Account farming: unique FPs BUT same /24 IP block, varied emails, low activity."""
    signups, trades = [], []
    for i in range(85):
        sid = f"s{start_id + i:04d}"
        ts = BASE_DATE + timedelta(days=rng.randint(0, 14), hours=rng.randint(0, 23))
        domain = rng.choice(REAL_DOMAINS + DISPOSABLE_DOMAINS[:2])
        email = f"acct{rng.randint(1000, 9999)}@{domain}"
        fp = _fp(f"aff003_unique_{i}_{rng.random()}")
        # same /24: prefix c0, varying host
        ip = _ip("c0", rng.randint(1, 254))
        country = rng.choice(COUNTRIES[:5])
        utm = rng.choice(UTM_SOURCES)
        s = make_signup(rng, sid, "aff_003", ts, email, fp, ip, country, utm)
        signups.append(s)
        first_dep = rng.uniform(10, 80)
        total_dep = first_dep * rng.uniform(1.0, 1.3)
        withdrawals = total_dep * rng.uniform(0.0, 0.15)
        t = make_trade_summary(rng, sid, "aff_003", first_dep, total_dep, withdrawals,
                               rng.randint(1, 8), rng.randint(1, 5))
        trades.append(t)
    return signups, trades


def gen_aff004(rng: random.Random, start_id: int) -> tuple[list, list]:
    """Mid quality: mix of real and disposable emails, moderate deposits, some dormant."""
    signups, trades = [], []
    for i in range(80):
        sid = f"s{start_id + i:04d}"
        ts = BASE_DATE + timedelta(days=rng.randint(0, 29), hours=rng.randint(0, 23))
        domain = rng.choice(REAL_DOMAINS if rng.random() > 0.35 else DISPOSABLE_DOMAINS)
        email = f"person{rng.randint(1000, 9999)}@{domain}"
        fp = _fp(f"aff004_{i}_{rng.random()}")
        ip = _ip(f"d{rng.randint(10,50)}", rng.randint(1, 254))
        country = rng.choice(COUNTRIES)
        utm = rng.choice(UTM_SOURCES)
        s = make_signup(rng, sid, "aff_004", ts, email, fp, ip, country, utm)
        signups.append(s)
        dormant = rng.random() < 0.35
        if dormant:
            t = make_trade_summary(rng, sid, "aff_004", 0.0, 0.0, 0.0, 0, 0)
        else:
            first_dep = rng.uniform(25, 150)
            total_dep = first_dep * rng.uniform(1.0, 1.8)
            withdrawals = total_dep * rng.uniform(0.1, 0.4)
            t = make_trade_summary(rng, sid, "aff_004", first_dep, total_dep, withdrawals,
                                   rng.randint(5, 30), rng.randint(3, 15))
        trades.append(t)
    return signups, trades


def gen_aff005(rng: random.Random, start_id: int) -> tuple[list, list]:
    """Mid quality with withdrawal pattern: decent deposits but high withdrawal-to-deposit ratio."""
    signups, trades = [], []
    for i in range(75):
        sid = f"s{start_id + i:04d}"
        ts = BASE_DATE + timedelta(days=rng.randint(0, 29), hours=rng.randint(0, 23))
        domain = rng.choice(REAL_DOMAINS + DISPOSABLE_DOMAINS[2:4])
        email = f"trader{rng.randint(1000, 9999)}@{domain}"
        fp = _fp(f"aff005_{i}_{rng.random()}")
        ip = _ip(f"e{rng.randint(10,60)}", rng.randint(1, 254))
        country = rng.choice(COUNTRIES)
        utm = rng.choice(UTM_SOURCES)
        s = make_signup(rng, sid, "aff_005", ts, email, fp, ip, country, utm)
        signups.append(s)
        first_dep = rng.uniform(50, 200)
        total_dep = first_dep * rng.uniform(1.1, 2.0)
        # High withdrawal ratio: 0.65-0.90
        withdrawals = total_dep * rng.uniform(0.65, 0.90)
        t = make_trade_summary(rng, sid, "aff_005", first_dep, total_dep, withdrawals,
                               rng.randint(5, 20), rng.randint(3, 12))
        trades.append(t)
    return signups, trades


def gen_aff006(rng: random.Random, start_id: int) -> tuple[list, list]:
    """Inconclusive: mixed signals — some good, some bad, no dominant pattern."""
    signups, trades = [], []
    shared_fp = _fp("aff006_shared")
    for i in range(78):
        sid = f"s{start_id + i:04d}"
        ts = BASE_DATE + timedelta(days=rng.randint(0, 29), hours=rng.randint(0, 23))
        if i % 5 == 0:
            domain = rng.choice(DISPOSABLE_DOMAINS)
            fp = shared_fp
            ip = _ip("f0", rng.randint(1, 3))
        else:
            domain = rng.choice(REAL_DOMAINS)
            fp = _fp(f"aff006_unique_{i}_{rng.random()}")
            ip = _ip(f"f{rng.randint(10, 99)}", rng.randint(1, 254))
        email = f"mixed{rng.randint(1000, 9999)}@{domain}"
        country = rng.choice(COUNTRIES)
        utm = rng.choice(UTM_SOURCES)
        s = make_signup(rng, sid, "aff_006", ts, email, fp, ip, country, utm)
        signups.append(s)
        dormant = rng.random() < 0.2
        if dormant:
            t = make_trade_summary(rng, sid, "aff_006", 0.0, 0.0, 0.0, 0, 0)
        else:
            first_dep = rng.uniform(20, 300)
            total_dep = first_dep * rng.uniform(1.0, 2.0)
            withdrawals = total_dep * rng.uniform(0.1, 0.5)
            t = make_trade_summary(rng, sid, "aff_006", first_dep, total_dep, withdrawals,
                                   rng.randint(2, 40), rng.randint(1, 20))
        trades.append(t)
    return signups, trades


def generate(output_dir: Path) -> None:
    rng = random.Random(SEED)

    all_signups, all_trades = [], []
    cursor = 1

    for gen_fn in [gen_aff001, gen_aff002, gen_aff003, gen_aff004, gen_aff005, gen_aff006]:
        s, t = gen_fn(rng, cursor)
        all_signups.extend(s)
        all_trades.extend(t)
        cursor += len(s)

    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "signups.json", "w") as f:
        json.dump(all_signups, f, indent=2)
    with open(output_dir / "deposit_and_trade_summary.json", "w") as f:
        json.dump(all_trades, f, indent=2)

    print(f"Generated {len(all_signups)} signups and {len(all_trades)} trade records.")
    counts = {}
    for s in all_signups:
        counts[s["affiliate_id"]] = counts.get(s["affiliate_id"], 0) + 1
    for aff, cnt in sorted(counts.items()):
        print(f"  {aff}: {cnt} signups")


if __name__ == "__main__":
    generate(Path(__file__).parent / "data")
