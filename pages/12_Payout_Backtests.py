import pandas as pd
import streamlit as st

from lottery.ui import setup_page,hero,caveat
from lottery.data import get_draws,latest_stored_info,load_results_meta
from lottery.crowd import latest_crowd_snapshot
from lottery.payout_backtests import payout_backtest,summarize_payout_backtest

setup_page('Payout Backtests · Lottery Lab','💶')
hero('Payout Backtests','Backtest ticket modes in euros using verified BST prize payouts. Compare normal and constrained anti-crowd conversions on the same historical draws.')

game=st.segmented_control('Game',['6/42','6/49'],default='6/49')

if game=='6/49':
    modes={
        '649_k22_4':'K22 — 4 tickets',
        '649_k22_6':'K22 — 6 tickets',
        '649_k22_11':'K22 — 11 tickets',
        '649_k22_16':'K22 — 16 tickets',
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
meta=load_results_meta(game)
crowd=latest_crowd_snapshot(game)

if meta.empty:
    st.warning('No verified payout metadata are stored for this game.')
    caveat(); st.stop()

strengths=(0.0,0.10,0.20,0.30) if not crowd.empty else (0.0,)
with st.spinner('Running payout-aware walk-forward backtest...'):
    bt=payout_backtest(
        game,mode,draws,meta,latest['draw_no'],
        crowd_snapshot=crowd,
        strengths=strengths,
        min_history=50,
    )
    summary=summarize_payout_backtest(bt)

if summary.empty:
    st.info('No overlap yet between historical mode targets and verified payout metadata.')
    caveat(); st.stop()

show=summary.copy()
show['strength_pct']=(100*show.strength).round().astype(int)
show['roi_pct']=(100*show.roi).round(1)

st.markdown('### Euro results')
st.dataframe(
    show[[
        'strength_pct','draws','stake_eur','payout_eur','net_eur','roi_pct',
        'winning_draws','payout3_eur','payout4_eur','payout5_eur','payout6_eur',
        'normalized_payout_eur','sharing_timing_eur'
    ]].rename(columns={
        'strength_pct':'Crowd strength %',
        'draws':'Draws',
        'stake_eur':'Stake €',
        'payout_eur':'Payout €',
        'net_eur':'Net €',
        'roi_pct':'ROI %',
        'winning_draws':'Winning draws',
        'payout3_eur':'From 3/6 €',
        'payout4_eur':'From 4/6 €',
        'payout5_eur':'From 5/6 €',
        'payout6_eur':'From 6/6 €',
        'normalized_payout_eur':'Normalized payout €',
        'sharing_timing_eur':'Payout timing / sharing €',
    }),
    use_container_width=True,hide_index=True
)

base=show.iloc[0]
nonzero=show[show.strength>0]
if len(nonzero):
    best=nonzero.sort_values('payout_eur',ascending=False).iloc[0]
    st.info(
        f"Across the currently verified payout sample, the best non-zero crowd setting for this mode is "
        f"{int(best.strength_pct)}% by realized payout: €{best.payout_eur:.2f} versus €{base.payout_eur:.2f} at 0%. "
        "This is descriptive only; the sample is small and payout outcomes are highly lumpy."
    )

c1,c2=st.columns(2)
with c1:
    st.markdown('#### Realized payout by strength')
    st.bar_chart(show.set_index('strength_pct')['payout_eur'],height=330)
with c2:
    st.markdown('#### Net result by strength')
    st.bar_chart(show.set_index('strength_pct')['net_eur'],height=330)

st.markdown('### Decomposition')
st.caption(
    'Normalized payout replaces each 3/4/5-match BST payout with the median payout for that tier in the stored verified sample. '
    'This gives a rough conversion component. The residual “payout timing / sharing” component shows whether wins happened on unusually high- or low-paying draws.'
)
decomp=show[[
    'strength_pct','normalized_change_vs_base_eur','sharing_timing_change_vs_base_eur','payout_change_vs_base_eur'
]].rename(columns={
    'strength_pct':'Crowd strength %',
    'normalized_change_vs_base_eur':'Conversion change vs base €',
    'sharing_timing_change_vs_base_eur':'Payout timing/sharing change vs base €',
    'payout_change_vs_base_eur':'Total payout change vs base €',
})
st.dataframe(decomp,use_container_width=True,hide_index=True)

with st.expander('Per-draw payout detail'):
    st.dataframe(bt.sort_values(['draw_no','strength'],ascending=[False,True]),use_container_width=True,hide_index=True,height=520)

st.warning(
    'This is a short recent sample because verified BST payout metadata currently cover draws 63–74. '
    'A 6/6 hypothetical on a draw with no actual jackpot winner is valued at the published jackpot for that draw; other tiers use the published per-winning-line payout.'
)
st.caption(
    'The anti-crowd variants do not alter the selected K-number pool. Any payout difference comes from ticket conversion and from whether those wins line up with historically more- or less-crowded prize tiers.'
)
caveat()
