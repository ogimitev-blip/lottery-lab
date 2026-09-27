from __future__ import annotations
import json
from lottery.data import load_draws_df
from lottery.models import current_pool_649
from lottery.wheels import build_broad_six,extend_sequence

ACTUAL={8,9,17,27,37,48}
df=load_draws_df("6/49")
draws=[list(map(int,row)) for row in df[[f"n{i}" for i in range(1,7)]].to_numpy().tolist()]
pool,adds,diag,score=current_pool_649(draws,22)
base=build_broad_six(pool,score,649)
tickets=extend_sequence(base,pool,score,55,20260917+490000)
hits=[len(set(map(int,t)) & ACTUAL) for t in tickets]
best=max(hits)
out={
  "pool":list(map(int,pool)),
  "lines":len(tickets),
  "cost_eur":49.5,
  "best_ticket_hits":best,
  "hit_hist":{str(h):sum(x==h for x in hits) for h in range(7)},
  "lines_3plus":sum(h>=3 for h in hits),
  "lines_4plus":sum(h>=4 for h in hits),
  "lines_5plus":sum(h>=5 for h in hits),
  "lines_6":sum(h==6 for h in hits),
  "best_lines":[{"line":i+1,"ticket":list(map(int,t)),"hits":hits[i]} for i,t in enumerate(tickets) if hits[i]==best]
}
print("RESULT_BEGIN")
print(json.dumps(out,indent=2))
print("RESULT_END")
