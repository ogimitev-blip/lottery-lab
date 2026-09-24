import streamlit as st
from lottery.ui import setup_page,hero,caveat
from lottery.data import next_draw_info,validate_history
from lottery.wheels import line_price
from lottery.version import APP_VERSION

setup_page('Lottery Lab','🎯')
hero('Lottery Lab','6/42 + 6/49 generation, official-data sync, visual history and prospective tracking.')

n42=next_draw_info('6/42');n49=next_draw_info('6/49')
c1,c2,c3,c4=st.columns(4)
c1.metric('6/42 production','K28')
c2.metric('6/49 production','K22')
c3.metric('Next draw',f"#{n42['draw_no']} · {n42['date']}")
c4.metric('6/49 next line',f"€{line_price('6/49',n49['draw_no']):.2f}",delta='Special draw' if line_price('6/49',n49['draw_no'])>0.90 else None)

st.markdown('### Workspaces')
st.page_link('pages/1_Generator.py',label='Generator — game, budget, pool mode and exact tickets',icon='🎟️')
st.page_link('pages/2_Past_Draws.py',label='Past Draws — K28/K22 overlays, frequency, gaps and pairs',icon='🗺️')
st.page_link('pages/3_Backtest.py',label='Backtest — 6/42 selection vs conversion',icon='📈')
st.page_link('pages/4_Model_Info.py',label='Model Info — exact production rules',icon='🧠')
st.page_link('pages/5_Update_Draws.py',label='Draw Database — view, add, correct or delete stored draws',icon='🗃️')
st.page_link('pages/6_Prospective_Ledger.py',label='Prospective Ledger — freeze plays before the draw',icon='🧾')
st.page_link('pages/7_Mode_Comparison.py',label='Mode Comparison — cost and jackpot mechanics side by side',icon='⚖️')

issues=[]
for g in ['6/42','6/49']:
    e,w=validate_history(g)
    if e:issues.append(f"{g}: {len(e)} error(s)")
if issues:st.error('Data validation: '+'; '.join(issues))
else:st.success('Core draw-data validation passed. Scheduled official-result sync is active for Thursday/Sunday after draws.')

st.caption(f'Lottery Lab {APP_VERSION}')
caveat()
