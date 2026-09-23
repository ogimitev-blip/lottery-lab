import streamlit as st
from lottery.ui import setup_page,hero,caveat
from lottery.data import load_draws_642,load_custom_wheel
from lottery.backtest import walk_forward_642
from lottery.visuals import draw_map,frequency_grid,gap_chart,rolling_frequency,pair_matrix,performance_timeline
setup_page('Past Draws · Lottery Lab','🗺️');hero('Past Draws','Draw map first; then frequency, gaps, rolling trends, pairs and model performance.')
draws=load_draws_642();wheel=load_custom_wheel();bt=walk_forward_642(tuple(map(tuple,draws)),tuple(map(tuple,wheel)),50,50)
c1,c2,c3,c4=st.columns([1,1,1,2]);window=c1.selectbox('Window',[20,50,100,len(draws)],index=1,format_func=lambda x:'All' if x==len(draws) else str(x));show_model=c2.toggle('Model overlay',True);show_repeat=c3.toggle('Repeat additions',False);c4.info('Green = draw inside K28 · Orange = drawn outside K28 · Cyan = repeat addition')
st.plotly_chart(draw_map(draws,window,bt,show_model,show_repeat),use_container_width=True)
t1,t2,t3,t4=st.tabs(['Frequency & gaps','Rolling trends','Pairs','Model performance'])
with t1:
    a,b=st.columns(2)
    with a: st.plotly_chart(frequency_grid(draws,window),use_container_width=True)
    with b:
        fig,g=gap_chart(draws);st.plotly_chart(fig,use_container_width=True)
        with st.expander('Gap table'):st.dataframe(g,use_container_width=True,hide_index=True)
with t2:
    nums=st.multiselect('Numbers',list(range(1,43)),default=[8,28,38],max_selections=8);roll=st.selectbox('Rolling window',[20,50,100])
    if nums:st.plotly_chart(rolling_frequency(draws,nums,roll),use_container_width=True)
with t3:
    st.caption('Exploratory only: pair/motif information did not improve the production jackpot-selection model in our tests.');st.plotly_chart(pair_matrix(draws,window),use_container_width=True)
with t4:
    st.plotly_chart(performance_timeline(bt),use_container_width=True);r=bt.iloc[0];a,b,c=st.columns(3);a.metric('Latest OOS K28',f'{int(r.pool_hits)}/6');b.metric('Best 50-line ticket',f'{int(r.best_ticket_hits)}/6');c.metric('OOS draws',len(bt))
st.caption('The supplied history has draw order but no calendar-date column, so v0.1 labels rows by draws-ago/index.');caveat()
