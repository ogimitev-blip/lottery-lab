import pandas as pd
import streamlit as st

from lottery.ui import setup_page,hero,caveat
from lottery.data import get_draws,load_research_archive
from lottery.models import current_pool_642,current_pool_649
from lottery.historylab import compare_history_depth,summarize_depth

setup_page('History Depth Lab · Lottery Lab','🕰️')
hero('History Depth Lab','Test whether adding older draws helps before changing the frozen production model.')

game=st.segmented_control('Game',['6/42','6/49'],default='6/42')
current=get_draws(game)
archive_df,archive=load_research_archive(game)

if game=='6/42':
    base_pool=current_pool_642(current,28)[0]
    ext_pool=current_pool_642(current+archive,28)[0]
else:
    base_pool=current_pool_649(current,22)[0]
    ext_pool=current_pool_649(current+archive,22)[0]

a,b,c,d=st.columns(4)
a.metric('Current stored history',len(current))
b.metric('Extra 2020–2023 draws',len(archive))
c.metric('Extended history',len(current)+len(archive))
d.metric('Current-pool overlap',f"{len(set(base_pool)&set(ext_pool))}/{len(base_pool)}")

st.markdown('### Current selection impact')
x,y=st.columns(2)
with x:
    st.caption('Production history only')
    st.code('  '.join(f'{n:02d}' for n in base_pool),language=None)
with y:
    st.caption('Production history + 2020–2023 research archive')
    st.code('  '.join(f'{n:02d}' for n in ext_pool),language=None)

added=sorted(set(ext_pool)-set(base_pool))
removed=sorted(set(base_pool)-set(ext_pool))
st.write(f"Changed by deeper history — added: **{added or 'none'}** · removed: **{removed or 'none'}**")

window=st.select_slider('Recent OOS comparison window',options=[50,100,150],value=150)
bt=compare_history_depth(game,current,archive,max_targets=window,min_history=50)
s=summarize_depth(bt)

st.markdown('### Leakage-free recent comparison')
m=st.columns(6)
m[0].metric('OOS draws',s.get('draws',0))
m[1].metric('Mean hits · baseline',f"{s.get('baseline_mean',0):.3f}")
m[2].metric('Mean hits · extended',f"{s.get('extended_mean',0):.3f}")
m[3].metric('P(5+) · baseline',f"{s.get('baseline_p5',0):.1%}")
m[4].metric('P(5+) · extended',f"{s.get('extended_p5',0):.1%}")
m[5].metric('P(6) extended',f"{s.get('extended_p6',0):.1%}")

w1,w2,w3=st.columns(3)
w1.metric('Extended better',s.get('extended_wins',0))
w2.metric('Tie',s.get('ties',0))
w3.metric('Baseline better',s.get('baseline_wins',0))

if s:
    if s.get('extended_mean',0)>s.get('baseline_mean',0) and s.get('extended_wins',0)>s.get('baseline_wins',0):
        st.info('In this window the deeper-history variant is directionally stronger. That is not sufficient by itself for production promotion; it still needs robustness/multiple-testing checks.')
    elif s.get('extended_mean',0)<s.get('baseline_mean',0):
        st.success('Current result: the deeper-history variant does not improve the frozen model in this window. Production therefore remains on the existing history depth.')
    else:
        st.info('Current result: no meaningful directional advantage from the deeper-history variant in this window.')

if not bt.empty:
    chart=bt[['draw_index_newest_first','baseline_hits','extended_hits']].sort_values('draw_index_newest_first',ascending=False)
    st.line_chart(chart.set_index('draw_index_newest_first'),height=360)
    with st.expander('Per-draw comparison'):
        st.dataframe(bt,use_container_width=True,hide_index=True,height=480)

st.warning(
    'This page is research-only. The 2020–2023 archive is deliberately NOT fed into the production K28/K22 model until the deeper-history variant earns promotion under the same robustness standards used elsewhere.'
)
st.caption(
    'BST itself provides yearly draw archives back to 1995 for 6/42 and 1958 for 6/49. The 2020–2023 research layer here is a BST-derived public archive mirror, kept separate from the production database so provenance and model changes remain auditable.'
)
caveat()
