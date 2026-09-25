import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from lottery.data import get_draws,latest_stored_info,load_results_meta
from lottery.crowd import latest_crowd_snapshot
from lottery.payout_backtests import payout_backtest,summarize_payout_backtest
import lottery.data as data

class DummyState(dict):
    pass

data.st.session_state=DummyState()

tests=[
    ("6/49","649_k22_4"),
    ("6/49","649_k22_6"),
    ("6/49","649_k22_11"),
    ("6/42","642_18"),
    ("6/42","642_30"),
    ("6/42","642_50"),
]

for game,mode in tests:
    draws=get_draws(game)
    latest=latest_stored_info(game)
    meta=load_results_meta(game)
    crowd=latest_crowd_snapshot(game)
    bt=payout_backtest(
        game,mode,draws,meta,latest["draw_no"],
        crowd_snapshot=crowd,
        strengths=(0.0,0.10,0.20,0.30),
        min_history=50,
    )
    summary=summarize_payout_backtest(bt)
    print("PAYOUT_RESULT",game,mode,summary.to_json(orient="records"))

print("PAYOUT_BACKTESTS_OK")
