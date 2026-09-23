from lottery.data import get_draws,next_draw_info,validate_history
from lottery.modes import modes_for_game,generate_mode
from lottery.wheels import line_price

class DummyState(dict):
    pass

# Streamlit session state is not needed for repository-backed draw loading in this smoke test.
import lottery.data as data
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
