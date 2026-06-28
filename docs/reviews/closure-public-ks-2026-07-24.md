# T4-2 Public dataKS Baseline acceptance and inspection

- Date of acceptance: 2026-07-24(Asia/Shanghai)
- Conclusions**BLOCKED**
- Reason: Neither open original file exists and neither ground-based real value baseline is recorded.

## Read-only Data Search

Implementation:

```bash
find <worktree> \
     <local-data-staging> \
  -type f \( \
    -iname 'cs-training.csv' -o \
    -iname 'application_train.csv' -o \
    -iname '*give*me*some*credit*' -o \
    -iname '*home*credit*default*risk*' \
  \) -print
```

Result: No output. No data are impersonated as publicly available using synthetic data, similar filenames or historical tasks of the platform.

## Machine door.

```bash
python scripts/ks_baseline.py --status
```

Result: Exit code`2`.

| Dataset| Original file| Manually fine-tuned baseline| Status|
|---|---|---|---|
| Give Me Some Credit | Missing| `null` | BLOCKED |
| Home Credit Default Risk | Missing| `null` | BLOCKED |

## Precision Completing Command

Give Me Some Credit:

```bash
python scripts/ks_baseline.py \
  --dataset give_me_some_credit \
  --input /absolute/path/to/cs-training.csv \
  --params-json @/absolute/path/to/reviewed-lgb-params.json \
  --record \
  --tuned-by "<name/team>" \
  --tuning-note "<method and review>"

python scripts/ks_baseline.py \
  --dataset give_me_some_credit \
  --input /absolute/path/to/cs-training.csv
```

Home Credit:

```bash
python scripts/ks_baseline.py \
  --dataset home_credit \
  --input /absolute/path/to/application_train.csv \
  --params-json @/absolute/path/to/reviewed-lgb-params.json \
  --record \
  --tuned-by "<name/team>" \
  --tuning-note "<method and review>"

python scripts/ks_baseline.py \
  --dataset home_credit \
  --input /absolute/path/to/application_train.csv
```

`--record` Original file savedSHA-256,Samples, characteristics,seed,split,Formula,
Complete parameters, emulations/The person responsible for the review and the time.Agent Runs are rejected and cannot be ground-based.
