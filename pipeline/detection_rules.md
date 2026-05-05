# Detection Rules

Rules are programmatically generated from computed features and classification results.
Each rule includes the trigger condition, affected affiliates, and both pandas and SQL implementations.

---

## Rule: `burst_signup_velocity`

**Description:** Detects affiliates with abnormally high signup rates within a single minute.

**Trigger:** `peak_signups_per_minute > 5`

**Currently Triggered By:** aff_001 (peak_signups_per_minute=22.0000, cls=synthetic_signups)

### Pandas Implementation

```python
import pandas as pd

# df is a DataFrame loaded from affiliate_features.json
flagged = df[df['peak_signups_per_minute'] > 5]
```

### SQL Implementation

```sql
SELECT affiliate_id, peak_signups_per_minute
FROM affiliate_features
WHERE peak_signups_per_minute > 5;
```

---

## Rule: `device_fingerprint_cluster`

**Description:** Detects affiliates where a high proportion of signups share device fingerprints.

**Trigger:** `device_fingerprint_reuse_rate > 0.4`

**Currently Triggered By:** aff_001 (device_fingerprint_reuse_rate=1.0000, cls=synthetic_signups)

### Pandas Implementation

```python
import pandas as pd

# df is a DataFrame loaded from affiliate_features.json
flagged = df[df['device_fingerprint_reuse_rate'] > 0.4]
```

### SQL Implementation

```sql
SELECT affiliate_id, device_fingerprint_reuse_rate
FROM affiliate_features
WHERE device_fingerprint_reuse_rate > 0.4;
```

---

## Rule: `ip_block_concentration`

**Description:** Detects affiliates where signups cluster within a single IP /24 block.

**Trigger:** `ip_24_concentration > 0.6`

**Currently Triggered By:** aff_001 (ip_24_concentration=1.0000, cls=synthetic_signups), aff_002 (ip_24_concentration=1.0000, cls=clean), aff_003 (ip_24_concentration=1.0000, cls=account_farming), aff_004 (ip_24_concentration=1.0000, cls=sloppy), aff_005 (ip_24_concentration=1.0000, cls=inconclusive), aff_006 (ip_24_concentration=1.0000, cls=inconclusive)

### Pandas Implementation

```python
import pandas as pd

# df is a DataFrame loaded from affiliate_features.json
flagged = df[df['ip_24_concentration'] > 0.6]
```

### SQL Implementation

```sql
SELECT affiliate_id, ip_24_concentration, ip_24_top_block
FROM affiliate_features
WHERE ip_24_concentration > 0.6;
```

---

## Rule: `disposable_email_cluster`

**Description:** Detects affiliates with a high rate of disposable or temporary email domains.

**Trigger:** `disposable_email_rate > 0.3`

**Currently Triggered By:** aff_001 (disposable_email_rate=1.0000, cls=synthetic_signups), aff_004 (disposable_email_rate=0.3250, cls=sloppy)

### Pandas Implementation

```python
import pandas as pd

# df is a DataFrame loaded from affiliate_features.json
flagged = df[df['disposable_email_rate'] > 0.3]
```

### SQL Implementation

```sql
SELECT affiliate_id, disposable_email_rate, disposable_email_count
FROM affiliate_features
WHERE disposable_email_rate > 0.3;
```

---

## Rule: `mass_dormancy`

**Description:** Detects affiliates where the majority of referred accounts never traded.

**Trigger:** `dormant_account_rate > 0.6`

**Currently Triggered By:** None

### Pandas Implementation

```python
import pandas as pd

# df is a DataFrame loaded from affiliate_features.json
flagged = df[df['dormant_account_rate'] > 0.6]
```

### SQL Implementation

```sql
SELECT affiliate_id, dormant_account_rate, dormant_account_count
FROM affiliate_features
WHERE dormant_account_rate > 0.6;
```

---

## Rule: `high_withdrawal_ratio`

**Description:** Detects affiliates where referred users withdraw most of their deposited funds.

**Trigger:** `withdrawal_rate > 0.7`

**Currently Triggered By:** aff_005 (withdrawal_rate=0.7851, cls=inconclusive)

### Pandas Implementation

```python
import pandas as pd

# df is a DataFrame loaded from affiliate_features.json
flagged = df[df['withdrawal_rate'] > 0.7]
```

### SQL Implementation

```sql
SELECT affiliate_id, withdrawal_rate, total_withdrawals_usd, total_deposits_usd
FROM affiliate_features
WHERE withdrawal_rate > 0.7;
```

---
