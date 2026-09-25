import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from lottery.ui import setup_page,hero,caveat
from lottery.crowd import latest_crowd_snapshot,load_crowd_history,snapshot_summary
from lottery.data import get_draws
from lottery.models import current_pool_642,current_pool_649

setup_page('Crowd & Sharing Risk · Lottery Lab','👥')
hero('Crowd & Sharing Risk','BST player-choice statistics are used only to estimate sharing risk. They do not alter the probability that a number is drawn.')

game=st.segmented_control('Game',['6/42','6/49'],default='6/49')
crowd=latest_crowd_snapshot(game)
history=load_crowd_history(game)
if crowd.empty:
    st.warning('No BST played-number snapshot stored for this game yet.')
    caveat(); st.stop()

s=snapshot_summary(crowd)
draws=get_draws(game)
if game=='6/42':
    pool=current_pool_642(draws,28)[0]
else:
    pool=current_pool_649(draws,22)[0]

a,b,c,d=st.columns(4)
a.metric('BST snapshot',f"#{s['draw']} · {s['date']}")
b.metric('Unique combinations played',f"{s['coverage_pct']:.2f}%")
c.metric('Average plays / number',f"{s['mean_played']:,.0f}")
d.metric('≤31 vs >31 popularity',f"{s['birthday_ratio']:.2f}×" if pd.notna(s['birthday_ratio']) else '—')

st.info(
    'Interpretation: lower played counts can be useful for reducing the chance of sharing a prize with other players. '
    'They do not make a number more likely to be drawn. The Generator therefore keeps the draw-selection model separate from the crowd layer.'
)

view=crowd.copy()
view['in_current_pool']=view.number.astype(int).isin(set(pool))
view['played_vs_mean_pct']=(100*view.played_vs_mean).round(1)
view['all_time_drawn_vs_mean_pct']=(100*view.all_time_drawn_count/view.all_time_drawn_count.mean()).round(1)

st.markdown('### Numbers played by the public')
fig=px.bar(
    view.sort_values('number'),
    x='number',y='played_count',
    hover_data=['popularity_rank','played_vs_mean_pct','in_current_pool'],
    labels={'number':'Number','played_count':'Times played in BST snapshot'}
)
fig.add_hline(y=view.played_count.mean(),line_dash='dash',annotation_text='Average')
fig.update_layout(height=480)
st.plotly_chart(fig,use_container_width=True)

c1,c2=st.columns(2)
with c1:
    st.markdown('#### Least played')
    st.dataframe(
        view.sort_values('played_count')[['number','played_count','played_vs_mean_pct','popularity_rank','in_current_pool']].head(12),
        use_container_width=True,hide_index=True
    )
with c2:
    st.markdown('#### Most played')
    st.dataframe(
        view.sort_values('played_count',ascending=False)[['number','played_count','played_vs_mean_pct','popularity_rank','in_current_pool']].head(12),
        use_container_width=True,hide_index=True
    )

st.markdown('### Long-run drawn frequency reference')
st.caption(
    'BST also publishes cumulative drawn counts from the creation of the game. This is useful as a descriptive long-run sanity check, '
    'but Lottery Lab does not treat historical frequency as proof that a number is due.'
)
freq=view[['number','all_time_drawn_count','all_time_drawn_vs_mean_pct','in_current_pool']].sort_values('all_time_drawn_count',ascending=False)
st.dataframe(freq,use_container_width=True,hide_index=True,height=420)

st.markdown('### Snapshot history')
snapshots=history[['snapshot_draw','snapshot_date','unique_coverage_pct']].drop_duplicates().sort_values('snapshot_date')
if len(snapshots)>1:
    st.line_chart(snapshots.set_index('snapshot_date')['unique_coverage_pct'],height=300)
else:
    st.caption('One full BST crowd snapshot is stored so far. The scheduled result sync now captures new full played-number snapshots when BST publishes them.')

with st.expander('Method and limitations'):
    st.markdown(
        '''
- **Crowd index** in Generator is the geometric mean of each ticket number's played-count ratio versus the all-number average. 100 is approximately average popularity; lower is less popular.
- BST publishes **marginal number counts**, not the number of people who selected each exact six-number ticket. Crowd index is therefore a proxy, not an exact duplicate-ticket probability.
- Birthday/date preferences can be seen by comparing numbers ≤31 with higher numbers, especially in 6/49.
- Anti-crowd conversion preserves the selected pool and ticket incidence structure, then gives more exposure to less-played selected numbers. It does not alter raw jackpot probability for a fixed number of distinct lines.
'''
    )

st.caption('Source snapshot: official BST statistics page. Future snapshots are archived prospectively so we can test whether player preferences are stable.')
caveat()
