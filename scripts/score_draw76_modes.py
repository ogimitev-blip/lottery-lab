from __future__ import annotations
import json
from lottery.data import load_draws
from lottery.modes import generate_mode

ACTUAL={
    "6/49":{8,9,17,27,37,48},
    "6/42":{2,5,23,28,29,41},
}
MODES={
    "6/49":["649_k22_4","649_k22_6","649_k22_11","649_k22_16","649_k22_22","649_k22_28","649_k22_33"],
    "6/42":["642_18","642_30","642_50","642_80","642_130"],
}

def score(game,mid):
    draws=load_draws(game)
    st=generate_mode(game,mid,draws,target_draw_no=76)
    actual=ACTUAL[game]
    hits=[len(set(map(int,t)) & actual) for t in st["tickets"]]
    ph=len(set(map(int,st["pool"])) & actual)
    best=max(hits)
    return {
        "game":game,
        "mode_id":mid,
        "cost_eur":float(st["cost"]),
        "pool_hits":ph,
        "best_ticket_hits":best,
        "lines_3plus":sum(h>=3 for h in hits),
        "lines_4plus":sum(h>=4 for h in hits),
        "lines_5plus":sum(h>=5 for h in hits),
        "lines_6":sum(h==6 for h in hits),
        "hit_hist":{str(h):sum(x==h for x in hits) for h in range(7)},
        "best_lines":[{"line":i+1,"ticket":list(map(int,t)),"hits":hits[i]} for i,t in enumerate(st["tickets"]) if hits[i]==best],
    }

out=[score(g,m) for g,ms in MODES.items() for m in ms]
print("DRAW76_MODE_SCORE_BEGIN")
print(json.dumps(out,indent=2))
print("DRAW76_MODE_SCORE_END")
