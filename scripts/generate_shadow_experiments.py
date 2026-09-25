import sys
from datetime import date
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import lottery.data as data
from lottery.data import get_draws,next_draw_info
from lottery.shadow import append_shadow_batch,read_shadow_rows

class DummyState(dict):
    pass

data.st.session_state=DummyState()

# Workflow trigger marker: freeze immediately after draw-data updates.
created=0
for game in ("6/42","6/49"):
    target=next_draw_info(game)
    # Never freeze a "prospective" batch for a draw whose calendar date has
    # already arrived. This prevents a delayed result sync from back-filling a
    # shadow play after the outcome could be known.
    if date.fromisoformat(target["date"]) <= date.today():
        print("SKIP_SHADOW",game,target["draw_no"],target["date"],"not future")
        continue
    new=append_shadow_batch(game,target,get_draws(game))
    created+=len(new)
    print("SHADOW_BATCH",game,target["draw_no"],target["date"],len(new))
    for row in new:
        print("SHADOW_ROW",row["shadow_id"],row["label"],row["crowd_strength"],row["notional_stake_eur"])

print("SHADOW_TOTAL_CREATED",created)
print("SHADOW_LEDGER_ROWS",len(read_shadow_rows()))
