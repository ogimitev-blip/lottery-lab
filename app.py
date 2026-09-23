import streamlit as st
from lottery.ui import setup_page,hero,caveat
setup_page('Lottery Lab','🎯');hero('Lottery Lab','6/42 + 6/49 generation, visual history and leakage-free research tools.')
c1,c2,c3,c4=st.columns(4);c1.metric('6/42 production','K28');c2.metric('6/49 production','K22');c3.metric('Repeat rule','2-draw flex');c4.metric('Prices','€0.80 / €0.90')
st.markdown('### Workspaces')
st.page_link('pages/1_Generator.py',label='Generator — choose game, pool mode and ticket system',icon='🎟️')
st.page_link('pages/2_Past_Draws.py',label='Past Draws — draw map, frequency, gaps and pairs',icon='🗺️')
st.page_link('pages/3_Backtest.py',label='Backtest — 6/42 selection vs conversion',icon='📈')
st.page_link('pages/4_Model_Info.py',label='Model Info — exact rules',icon='🧠')
st.page_link('pages/5_Update_Draws.py',label='Update Draws — add the newest 6/42 / 6/49 result',icon='➕')
st.info('The generator now separates the GAME from the MODE. 6/49 supports the K22 production family and K26 shadow family; 6/42 supports K28 custom systems.')
caveat()
