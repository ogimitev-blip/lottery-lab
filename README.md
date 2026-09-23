# Lottery Lab

Streamlit control panel for the Bulgarian Toto 2 6/42 and 6/49 research workflow.

## Current capabilities

- **6/42 production:** K28 smooth + overdue λ=1 + two-draw repeat rule.
- **6/49 production:** K22 ensemble + overdue λ=0.75 + two-draw repeat rule.
- **6/49 K26:** shadow/challenger only.
- Ticket modes:
  - 6/42: 6 / 18 / 30 / 50 / 80 / 130 custom lines + official System 36 benchmark.
  - 6/49: K22 and K26 families with 6 / 11 / 16 / 22 / 28 / 33 lines.
- Budget filtering and visible Production / Benchmark / Shadow / High-spend labels.
- Dynamic 6/49 special-draw pricing for the published 2026 special draws.
- Interactive Draw Map with historical K28 and K22 pool overlays.
- Frequency grid, gaps, rolling frequency and pair co-occurrence.
- Leakage-free 6/42 backtesting.
- Prospective play ledger: freeze an exact play before the result, then score it later.
- Mode comparison screen.
- Data-quality checks.

## Official result syncing

GitHub Actions runs after Thursday and Sunday draws and checks the official BST result pages at `info.toto.bg`.

When a new official result is published it updates:

- `data/draws_642.csv`
- `data/draws_649.csv`
- `data/results_meta_642.csv`
- `data/results_meta_649.csv`
- `data/sync_state.json`

The workflow also performs a one-time 2026 backfill of draw numbers, dates, jackpots and 3/4/5/6 payout metadata when official result pages can be matched to the local history.

Manual entry remains available inside the app as a fallback.

## Prospective ledger

The Generator can **Stage as prospective play**. This freezes the game, target draw, model version, mode, pool, repeat additions, tickets and stake before the result.

For permanent in-app persistence, add these only to Streamlit Community Cloud **Secrets**:

```toml
ADMIN_PASSWORD = "choose-a-private-password"
GITHUB_TOKEN = "github_pat_..."
```

The GitHub token should be fine-grained, restricted to this repository, with **Contents: Read and write**.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy

Repository: `ogimitev-blip/lottery-lab`  
Branch: `main`  
Main file: `app.py`

## Interpretation

Historical patterns and backtests are descriptive research tools. They do not establish that future lottery draws are predictable. Keep gambling spend fixed and pre-committed.
