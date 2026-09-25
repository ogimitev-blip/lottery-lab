import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from lottery.data import get_draws,latest_stored_info
from lottery.crowd import load_crowd_history
from lottery.constrained_backtests import backtest_constrained_crowd_grid,summarize_constrained_grid
import lottery.data as data

class DummyState(dict):
    pass

data.st.session_state=DummyState()

tests=[
    ("6/49","649_k22_4"),
    ("6/49","649_k22_6"),
    ("6/42","642_18"),
    ("6/42","642_30"),
    ("6/42","642_50"),
]

for game,mode in tests:
    draws=get_draws(game)
    latest=latest_stored_info(game)
    crowd=load_crowd_history(game)
    bt=backtest_constrained_crowd_grid(
        game,mode,draws,crowd,latest["draw_no"],
        strengths=(0.0,0.10,0.20,0.30),
        max_targets=100,min_history=50,
    )
    summary=summarize_constrained_grid(bt)
    print("CONSTRAINED_RESULT",game,mode,summary.to_json(orient="records"))

print("CONSTRAINED_GRID_OK")
