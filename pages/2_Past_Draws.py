import streamlit as st
from lottery.ui import setup_page,hero,caveat
from lottery.data import get_draws,get_draw_labels,load_custom_wheel
from lottery.backtest import walk_forward_642,walk_forward_pool_649
from lottery.visuals import draw_map,frequency_grid,gap_chart,rolling_frequency,pair_matrix,performance_timeline

setup_page('Past Draws · Lottery Lab','🗺️')
hero('Past Draws','Draw map first; then frequency, gaps, rolling trends, pairs and model performance.')

game=st.segmented_control('Game',['6/42','6/49'],default='6/42')
draws=get_draws(game);labels=get_draw_labels(game);N=42 if game=='6/42' else 49
if game=='6/42':
    wheel=load_custom_wheel();bt=walk_forward_642(tuple(map(tuple,draws)),tuple(map(tuple,wheel)),50,50);overlay=bt
else:
    bt=None;overlay=walk_forward_pool_649(tuple(map(tuple,draws)),50,22)

c1,c2,c3,c4=st.columns([1,1,1,2])
window=c1.selectbox('Window',[20,50,100,len(draws)],index=1,format_func=lambda x:'All' if x==len(draws) else str(x))
show_model=c2.toggle('Model overlay',True)
show_repeat=c3.toggle('Repeat additions',False)
if game=='6/42':c4.info('Green = drawn inside historical K28 · Orange = drawn outside K28 · Cyan = repeat addition')
else:c4.info('Green = drawn inside historical K22 · Orange = drawn outside K22 · Cyan = repeat addition')

st.plotly_chart(draw_map(draws,window,N,labels,overlay,show_model,show_repeat),use_container_width=True)

t1,t2,t3,t4=st.tabs(['Frequency & gaps','Rolling trends','Pairs','Model performance'])
with t1:
    a,b=st.columns(2)
    with a:st.plotly_chart(frequency_grid(draws,window,N),use_container_width=True)
    with b:
        fig,g=gap_chart(draws,N);st.plotly_chart(fig,use_container_width=True)
        with st.expander('Gap table'):st.dataframe(g,use_container_width=True,hide_index=True)
with t2:
    nums=st.multiselect('Numbers',list(range(1,N+1)),default=[8,28,38],max_selections=8);roll=st.selectbox('Rolling window',[20,50,100])
    if nums:st.plotly_chart(rolling_frequency(draws,nums,roll),use_container_width=True)
with t3:
    st.caption('Exploratory only: co-occurrence does not by itself imply higher future draw probability.')
    st.plotly_chart(pair_matrix(draws,window,N),use_container_width=True)
with t4:
    if bt is not None:st.plotly_chart(performance_timeline(bt),use_container_width=True)
    else:
        d=overlay.sort_values('draw_index_newest_first',ascending=False).reset_index(drop=True)
        st.line_chart(d[['pool_hits']],height=420)
        st.caption('6/49 currently shows K22 selection-pool capture. Ticket-conversion history is kept separate from the pool model.')
caveat()
