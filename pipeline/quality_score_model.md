# Quality Score Model — v1.0

## Overview
Scores are computed deterministically from affiliate feature vectors and classification labels.
Range: 0–100. Higher scores indicate higher traffic quality.

## Base Score
`base_score = 100`

## Penalties

### Classification Penalty
| Classification     | Penalty |
|--------------------|---------|
| synthetic_signups  | -40     |
| account_farming    | -35     |
| incentive_abuse    | -30     |
| sloppy             | -15     |
| inconclusive       | -5      |
| clean              | 0       |

### Device Fingerprint Reuse Penalty
- `device_fingerprint_reuse_rate > 0.5` → -15
- `device_fingerprint_reuse_rate > 0.2` → -7

### Signup Velocity Penalty
- `peak_signups_per_minute > 10` → -15
- `peak_signups_per_minute > 3` → -7

### IP /24 Concentration Penalty
- `ip_24_concentration > 0.7` → -10
- `ip_24_concentration > 0.4` → -5

### Disposable Email Penalty
- `disposable_email_rate > 0.5` → -10
- `disposable_email_rate > 0.2` → -5

### Dormant Account Penalty
- `dormant_account_rate > 0.7` → -10
- `dormant_account_rate > 0.4` → -5

## Bonuses

### Active Days Bonus
- `avg_first_30d_active_days > 10` → +10
- `avg_first_30d_active_days > 5` → +5

### Trade Count Bonus
- `avg_trades_count > 30` → +10
- `avg_trades_count > 10` → +5

### Deposit Retention Bonus
- `deposit_retention_rate > 0.5` → +10
- `deposit_retention_rate > 0.3` → +5

### Deposit Size Bonus
- `avg_total_deposits_usd > 200` → +5

## Final Score
`final_score = clamp(base_score + sum(bonuses) + sum(penalties), 0, 100)`

## Risk Level Mapping
| Score Range | Risk Level |
|-------------|------------|
| 75–100      | low        |
| 50–74       | medium     |
| 25–49       | high       |
| 0–24        | critical   |
