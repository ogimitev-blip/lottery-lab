import streamlit as st
from lottery.ui import setup_page,hero,caveat
from lottery.data import load_draws_642,load_custom_wheel,load_system36
from lottery.models import current_pool_642
from lottery.wheels import map_positions,ticket_frame,cost_642
setup_page('Generator · Lottery Lab','🎟️');hero('Ticket & System Generator','Generate the current K28 pool, inspect scores, and map the pool into a fixed system.')
draws=load_draws_642();pool,adds,diag=current_pool_642(draws);custom=load_custom_wheel();sys36=load_system36()
system=st.selectbox('System',['Custom K28 — 18 lines','Custom K28 — 30 lines','Custom K28 — 50 lines','Custom K28 — 80 lines','Custom K28 — 130 lines','Official System 36 — 50 lines'],index=2)
positions=sys36 if system.startswith('Official') else custom[:int(system.split('—')[1].split()[0])]
tickets=map_positions(pool,positions);n=len(tickets)
m1,m2,m3,m4=st.columns(4);m1.metric('Pool',28);m2.metric('Lines',n);m3.metric('Cost',f'€{cost_642(n):.2f}');m4.metric('Repeat additions',', '.join(map(str,adds)) if adds else 'none')
st.markdown('### Current K28 pool');st.code('  '.join(f'{x:02d}' for x in pool),language=None)
with st.expander('Number scores and ranks'):
    d=diag.copy();d.score=d.score.round(3);st.dataframe(d,use_container_width=True,hide_index=True)
st.markdown('### Tickets');tf=ticket_frame(tickets);st.dataframe(tf,use_container_width=True,hide_index=True,height=520)
st.download_button('Download CSV',tf.to_csv(index=False).encode(),file_name=f'642_{n}_tickets.csv',mime='text/csv')
st.download_button('Download text','\n'.join(' '.join(f'{x:02d}' for x in t) for t in tickets).encode(),file_name=f'642_{n}_tickets.txt',mime='text/plain');caveat()
