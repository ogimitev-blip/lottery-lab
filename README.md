# Lottery Lab

Streamlit control panel for the Bulgarian Toto 2 6/42 and 6/49 research workflow.

## Current capabilities

- **6/42 production:** K28 smooth + overdue λ=1 + two-draw repeat rule.
- **6/49 production:** K22 ensemble + overdue λ=0.75 + two-draw repeat rule.
- **6/49 K26:** shadow/challenger only.
- Ticket modes:
  - 6/42: 6 / 18 / 30 / 50 / 80 / 130 custom lines + System 36 benchmark + exact official Systems 46 / 28 / 30 / 107 / 105 / 10 / 76 / 104.
  - 6/49: K22 family with 4 / 6 / 11 / 16 / 22 / 28 / 33 lines, K26 shadow family with 6 / 11 / 16 / 22 / 28 / 33 lines, + exact official Systems 46 / 28 / 30 / 107 / 105 / 10 / 76 / 118.
- Budget filtering and visible Production / Benchmark / Shadow / High-spend labels.
- Dynamic 6/49 special-draw pricing for the published 2026 special draws.
- Interactive Draw Map with historical K28 and K22 pool overlays.
- Frequency grid, gaps, rolling frequency and pair co-occurrence.
- Leakage-free 6/42 backtesting.
- Prospective play ledger: freeze an exact play before the result, then score it later.
- Prospective shadow promotion gate: paired baseline-vs-anti-crowd evidence accumulates forward-only; <30 draws is observation-only, 30–49 interim review, 50+ required before promotion review can even be considered.
- Mode comparison screen.
- Data-quality checks.
- Crowd / sharing-risk dashboard using BST played-number counts and unique-combination coverage.
- Experimental anti-crowd conversion that leaves selection and wheel incidence structure unchanged.
- History Depth Lab with a separate 2020–2023 research archive; older draws are not fed into production unless they pass robustness testing.

## Official result syncing

A scheduled ChatGPT task checks the official BST result pages after Thursday and Sunday draws. It reads `data/sync_state.json` and, only when a newer official draw is fully verifiable, updates the GitHub repository with winning numbers and payout metadata. Streamlit then redeploys from `main`.

A direct GitHub Actions scraper was tested, but BST's Radware browser verification blocks GitHub-hosted runner IPs. That workflow is therefore kept as a **manual probe only**, not relied on for production syncing.

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
