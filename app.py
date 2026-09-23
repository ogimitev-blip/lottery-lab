import streamlit as st
from lottery.ui import setup_page,hero,caveat
setup_page('Lottery Lab','🎯');hero('Lottery Lab','6/42 ticket generation, visual history and leakage-free backtesting.')
c1,c2,c3,c4=st.columns(4);c1.metric('Production pool','K28');c2.metric('Selection','Smooth + overdue');c3.metric('Repeat rule','2-draw flex');c4.metric('Line price','€0.80')
st.markdown('### Workspaces')
st.page_link('pages/1_Generator.py',label='Generator — current pool and tickets',icon='🎟️')
st.page_link('pages/2_Past_Draws.py',label='Past Draws — draw map, frequency, gaps and pairs',icon='🗺️')
st.page_link('pages/3_Backtest.py',label='Backtest — selection vs conversion',icon='📈')
st.page_link('pages/4_Model_Info.py',label='Model Info — exact rules',icon='🧠')
st.info('v0.1 starts with 6/42. Replace data/draws_642.csv when new draws are added.');caveat()
