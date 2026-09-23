import streamlit as st
from lottery.ui import setup_page,hero,caveat
from lottery.data import get_draws
from lottery.modes import modes_for_game,generate_mode
from lottery.wheels import ticket_frame

setup_page('Generator · Lottery Lab','🎟️')
hero('Ticket & System Generator','Choose the game first, then the production/shadow mode and the number of lines.')

game=st.segmented_control('Game',['6/42','6/49'],default='6/42')
modes=modes_for_game(game); labels={m[0]:m[1] for m in modes}
default='642_50' if game=='6/42' else '649_k22_6'
mode_id=st.selectbox('Mode',[m[0] for m in modes],index=[m[0] for m in modes].index(default),format_func=lambda x:labels[x])

draws=get_draws(game)
state=generate_mode(game,mode_id,draws); tickets=state['tickets']

m1,m2,m3,m4=st.columns(4)
m1.metric('Selection pool',f"K{state['k']}")
m2.metric('Lines',len(tickets))
m3.metric('Cost',f"€{state['cost']:.2f}")
m4.metric('Repeat additions',', '.join(map(str,state['additions'])) if state['additions'] else 'none')

if game=='6/49' and state['k']==26:
    st.warning('K26 is a shadow/challenger mode. K22 remains the production 6/49 selection pool.')
elif game=='6/42':
    st.caption('6/42 uses the frozen K28 smooth + overdue λ=1 + repeat-rule selection model.')

st.markdown(f"### Current K{state['k']} pool")
st.code('  '.join(f'{x:02d}' for x in state['pool']),language=None)

with st.expander('Number scores, ranks and gaps'):
    d=state['diagnostics'].copy(); d.score=d.score.round(3)
    st.dataframe(d,use_container_width=True,hide_index=True)

st.markdown('### Tickets')
tf=ticket_frame(tickets); st.dataframe(tf,use_container_width=True,hide_index=True,height=540)
slug=mode_id.replace('/','-')
st.download_button('Download CSV',tf.to_csv(index=False).encode(),file_name=f'{game.replace("/","")}_{slug}.csv',mime='text/csv')
st.download_button('Download text','\n'.join(' '.join(f'{x:02d}' for x in t) for t in tickets).encode(),file_name=f'{game.replace("/","")}_{slug}.txt',mime='text/plain')
caveat()
