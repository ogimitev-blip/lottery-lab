import json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from lottery.data import get_draws,latest_stored_info,load_research_archive
from lottery.crowd import load_crowd_history
from lottery.research_backtests import backtest_mode,summarize_mode_backtest,backtest_crowd_layer,summarize_crowd_backtest
from lottery.historylab import compare_history_depth,summarize_depth
import lottery.data as data

class DummyState(dict): pass
data.st.session_state=DummyState()

def emit(label,obj):
    print("RESEARCH_RESULT",label,json.dumps(obj,sort_keys=True))

for game,modes in [
    ("6/49",["649_k22_4","649_k22_6","649_k22_11","649_k22_33","649_sys46"]),
    ("6/42",["642_18","642_30","642_50","642_sys46"]),
]:
    draws=get_draws(game)
    for mid in modes:
        t=time.time()
        bt=backtest_mode(game,mid,draws,max_targets=50,min_history=50)
        s=summarize_mode_backtest(bt)
        s["seconds"]=round(time.time()-t,2)
        emit(f"MODE {game} {mid}",s)

for game,mid in [("6/49","649_k22_4"),("6/49","649_k22_6"),("6/42","642_18"),("6/42","642_50")]:
    draws=get_draws(game)
    latest=latest_stored_info(game)
    crowd=load_crowd_history(game)
    bt=backtest_crowd_layer(game,mid,draws,crowd,latest["draw_no"],max_targets=100,min_history=50)
    emit(f"CROWD {game} {mid}",summarize_crowd_backtest(bt))

for game in ["6/42","6/49"]:
    draws=get_draws(game)
    _,archive=load_research_archive(game)
    for window in [50,100,150]:
        bt=compare_history_depth(game,draws,archive,max_targets=window,min_history=50)
        emit(f"HISTORY {game} {window}",summarize_depth(bt))

print("RESEARCH_BACKTESTS_OK")
