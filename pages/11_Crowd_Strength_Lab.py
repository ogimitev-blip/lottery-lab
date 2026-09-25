import pandas as pd
import streamlit as st

from lottery.ui import setup_page,hero,caveat
from lottery.data import get_draws,latest_stored_info
from lottery.crowd import load_crowd_history
from lottery.constrained_backtests import backtest_constrained_crowd_grid,summarize_constrained_grid

setup_page('Crowd Strength Lab · Lottery Lab','🎚️')
hero('Crowd Strength Lab','Test 0–30% constrained anti-crowd conversion without changing the selected K-number pool.')

game=st.segmented_control('Game',['6/42','6/49'],default='6/49')

if game=='6/49':
    modes={
        '649_k22_4':'K22 — 4 tickets',
        '649_k22_6':'K22 — 6 tickets',
        '649_k22_11':'K22 — 11 tickets',
    }
    default='649_k22_4'
else:
    modes={
        '642_18':'K28 — 18 lines',
        '642_30':'K28 — 30 lines',
        '642_50':'K28 — 50 lines',
    }
    default='642_18'

mode=st.selectbox('Mode',list(modes),index=list(modes).index(default),format_func=lambda x:modes[x])
draws=get_draws(game)
latest=latest_stored_info(game)
crowd=load_crowd_history(game)

with st.spinner('Running constrained crowd-strength grid...'):
    bt=backtest_constrained_crowd_grid(
        game,mode,draws,crowd,latest['draw_no'],
        strengths=(0.0,0.10,0.20,0.30),
        max_targets=100,min_history=50,
    )
    summary=summarize_constrained_grid(bt)

if summary.empty:
    st.info('No strictly pre-target crowd snapshot is available yet.')
    caveat()
    st.stop()

show=summary.copy()
show['strength_pct']=(100*show.strength).round().astype(int)
show['crowd_reduction_pct_display']=(100*show.crowd_reduction_pct).round(2)
show['model_utility_pct']=(100*show.avg_model_utility_ratio).round(2)
show['p3plus_pct']=(100*show.p3plus).round(1)
show['p4plus_pct']=(100*show.p4plus).round(1)
show['p5plus_pct']=(100*show.p5plus).round(1)

st.markdown('### Grid result')
st.dataframe(
    show[[
        'strength_pct','draws','avg_crowd_index','crowd_reduction_pct_display',
        'mean_best_hits','p3plus_pct','p4plus_pct','p5plus_pct',
        'avg_swaps','model_utility_pct'
    ]].rename(columns={
        'strength_pct':'Crowd strength %',
        'draws':'Eligible draws',
        'avg_crowd_index':'Avg crowd index',
        'crowd_reduction_pct_display':'Crowd reduction %',
        'mean_best_hits':'Mean best hits',
        'p3plus_pct':'P(3+) %',
        'p4plus_pct':'P(4+) %',
        'p5plus_pct':'P(5+) %',
        'avg_swaps':'Avg swaps',
        'model_utility_pct':'Model utility retained %',
    }),
    use_container_width=True,hide_index=True
)

c1,c2=st.columns(2)
with c1:
    chart=show.set_index('strength_pct')[['avg_crowd_index']]
    st.line_chart(chart,height=330)
    st.caption('Lower crowd index = lower marginal number popularity in the BST snapshot.')
with c2:
    chart=show.set_index('strength_pct')[['mean_best_hits']]
    st.line_chart(chart,height=330)
    st.caption('Conversion quality: historical best ticket hits per draw.')

base=show.iloc[0]
nonzero=show[show.strength>0].copy()
if len(nonzero):
    stable=nonzero[
        (nonzero.p3plus>=base.p3plus) &
        (nonzero.p4plus>=base.p4plus) &
        (nonzero.mean_best_hits>=base.mean_best_hits-0.05)
    ]
    if len(stable):
        best=stable.sort_values(['crowd_reduction_pct','strength'],ascending=[False,True]).iloc[0]
        st.info(
            f"In this small crowd-snapshot sample, {int(best.strength_pct)}% is the strongest tested constraint "
            f"that did not reduce P(3+) or P(4+) and kept mean best hits within 0.05 of baseline. "
            f"Crowd index fell by {100*best.crowd_reduction_pct:.2f}%."
        )
    else:
        st.warning('None of the non-zero crowd strengths met the simple no-conversion-deterioration screen in this sample.')

with st.expander('Per-draw grid results'):
    st.dataframe(bt,use_container_width=True,hide_index=True,height=500)

st.warning(
    'The current crowd sample is short because Lottery Lab only has complete BST played-number snapshots prospectively from draw 62 onward. '
    'Treat differences as exploratory. Promotion requires more snapshots and stable results across modes.'
)
st.caption(
    'Constraint definition: a number can replace a ticket position only when its model score is within the selected percentage of the current pool score range. '
    'The optimizer then reduces exposure-weighted public popularity inside that allowed neighborhood.'
)
caveat()
