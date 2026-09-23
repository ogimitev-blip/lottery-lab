# Lottery Lab

Streamlit app for the 6/42 lottery research workflow.

## Included

- Current **K28 production pool** generator.
- Selection model: smooth frequency across 20/50/100/all-history windows + overdue adjustment + two-draw repeat rule.
- Custom nested systems: **18 / 30 / 50 / 80 / 130 lines**.
- Official **System 36** comparison.
- Interactive past-draw map.
- Fixed-position 1–42 frequency heatmap.
- Gap / overdue visualization.
- Rolling 20 / 50 / 100-draw frequency trends.
- Pair co-occurrence matrix.
- Selection-vs-conversion performance timeline.
- Leakage-free walk-forward backtest page.
- CSV/text ticket export.

The bundled 6/42 history is newest-first and currently includes the **20 Sep 2026** draw.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Go to https://share.streamlit.io and sign in with GitHub.
2. Click **Create app**.
3. Choose repository `ogimitev-blip/lottery-lab`.
4. Branch: `main`.
5. Main file path: `app.py`.
6. Click **Deploy**.

Community Cloud watches GitHub, so future commits are reflected in the deployed app.

## Updating draw history

`data/draws_642.csv` is newest-first. Add a new draw as the first data row beneath the header.

## Interpretation

Historical charts and backtests describe past behavior. They do not establish that future lottery draws are predictable. Keep any gambling spend fixed and pre-committed.
