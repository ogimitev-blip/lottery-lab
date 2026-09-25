import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from lottery.data import get_draws,next_draw_info,validate_history
from lottery.modes import modes_for_game,generate_mode
from lottery.wheels import line_price
import lottery.data as data

class DummyState(dict):
    pass

data.st.session_state = DummyState()

for game in ["6/42","6/49"]:
    draws=get_draws(game)
    assert len(draws)>200,(game,len(draws))
    errors,_=validate_history(game)
    assert not errors,(game,errors[:3])
    target=next_draw_info(game)
    for m in modes_for_game(game):
        s=generate_mode(game,m["id"],draws,target["draw_no"])
        assert len(s["pool"])==m["k"]
        assert len(set(s["pool"]))==m["k"]
        assert len(s["tickets"])==m["lines"]
        assert all(len(t)==6 and len(set(t))==6 for t in s["tickets"])
        maxn=42 if game=="6/42" else 49
        assert all(1<=x<=maxn for t in s["tickets"] for x in t)

assert line_price("6/49",75)==1.00
assert line_price("6/49",74)==0.90
assert line_price("6/42",75)==0.80
print("SMOKE_OK")


# 6/49 four-ticket production mode: 24 slots should cover all K22 numbers,
# with exactly two numbers repeated once.
draws=get_draws("6/49")
target=next_draw_info("6/49")
s=generate_mode("6/49","649_k22_4",draws,target["draw_no"])
assert len(s["tickets"])==4
flat=[n for t in s["tickets"] for n in t]
assert len(flat)==24
assert len(set(flat))==22
counts={n:flat.count(n) for n in set(flat)}
assert sorted(counts.values()).count(2)==2
assert max(counts.values())==2
print("K22_FOUR_OK",s["tickets"])


from lottery.crowd import latest_crowd_snapshot,score_ticket_frame,anti_crowd_remap,snapshot_summary
from lottery.data import load_research_archive
from lottery.historylab import compare_history_depth,summarize_depth

for game in ["6/42","6/49"]:
    crowd=latest_crowd_snapshot(game)
    assert not crowd.empty
    expected=42 if game=="6/42" else 49
    assert len(crowd)==expected
    assert crowd.number.nunique()==expected
    s=snapshot_summary(crowd)
    assert s["coverage_pct"]>0
    draws=get_draws(game)
    target=next_draw_info(game)
    mode_id="642_18" if game=="6/42" else "649_k22_4"
    state=generate_mode(game,mode_id,draws,target["draw_no"])
    scored=score_ticket_frame(state["tickets"],crowd)
    assert len(scored)==len(state["tickets"])
    remap,mapping,meta=anti_crowd_remap(state["pool"],state["tickets"],crowd)
    assert len(remap)==len(state["tickets"])
    assert len(set(remap))==len(remap)
    assert all(len(t)==6 and len(set(t))==6 for t in remap)
print("CROWD_OK")

for game in ["6/42","6/49"]:
    current=get_draws(game)
    _,archive=load_research_archive(game)
    assert len(archive)==441
    bt=compare_history_depth(game,current,archive,max_targets=150,min_history=50)
    sm=summarize_depth(bt)
    print("HISTORY_DEPTH",game,sm)


from lottery.shadow import summarize_shadow_pairs,shadow_research_scoreboard

synthetic=[]
for draw_no in range(1,51):
    synthetic.append({
        "status":"scored","game":"6/49","target_draw_no":draw_no,"mode_id":"649_k22_6",
        "label":"K22-6 base","crowd_strength":0.0,"best_ticket_hits":3,
        "winning_lines_3plus":1,"notional_payout_eur":10.0,"avg_crowd_index":100.0,
    })
    synthetic.append({
        "status":"scored","game":"6/49","target_draw_no":draw_no,"mode_id":"649_k22_6",
        "label":"K22-6 crowd 30%","crowd_strength":0.30,"best_ticket_hits":3,
        "winning_lines_3plus":1,"notional_payout_eur":10.0,"avg_crowd_index":95.0,
    })
gate=summarize_shadow_pairs(synthetic)
assert len(gate)==1
assert int(gate.iloc[0].prospective_draws)==50
assert gate.iloc[0].sample_gate=="ELIGIBLE_FOR_PROMOTION_REVIEW"
assert round(float(gate.iloc[0].avg_crowd_reduction_pct),6)==5.0
print("SHADOW_GATE_OK")

score=shadow_research_scoreboard(synthetic)
assert len(score)==1
row=score.iloc[0]
assert int(row.prospective_draws)==50
assert row.evidence_maturity=="MATURE_REVIEW_SAMPLE"
assert int(row.best_hit_wins)==0 and int(row.best_hit_losses)==0 and int(row.best_hit_ties)==50
assert round(float(row.nondegradation_rate_pct),6)==100.0
assert round(float(row.avg_crowd_reduction_pct),6)==5.0
assert int(row.p3_net)==0
print("SHADOW_SCOREBOARD_OK")
