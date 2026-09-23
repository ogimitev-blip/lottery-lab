import streamlit as st
from lottery.ui import setup_page,hero,caveat
from lottery.data import get_draws,next_draw_info,validate_history
from lottery.modes import modes_for_game,generate_mode
from lottery.wheels import ticket_frame,line_price
from lottery.ledger import make_play,append_session
from lottery.version import APP_VERSION,MODEL_642,MODEL_649,WHEEL_642,WHEEL_649

setup_page('Generator · Lottery Lab','🎟️')
hero('Ticket & System Generator','Choose the game, spending envelope and mode. Production, benchmark and shadow modes are kept visibly separate.')

game=st.segmented_control('Game',['6/42','6/49'],default='6/42')
target=next_draw_info(game)
price=line_price(game,target['draw_no'])

errors,warnings=validate_history(game)
if errors:
    st.error('Data-quality errors detected: '+'; '.join(errors[:3]))
if warnings:
    st.warning('Data-quality note: '+'; '.join(warnings[:2]))

c1,c2,c3=st.columns([1,1,1])
c1.metric('Target draw',f"#{target['draw_no']}")
c2.metric('Draw date',target['date'])
c3.metric('Line price',f"€{price:.2f}",delta='Special draw' if game=='6/49' and price>0.90 else None)

modes=modes_for_game(game)
input_mode=st.radio('How do you want to choose?', ['Choose mode','Filter by budget'],horizontal=True)
eligible=modes
if input_mode=='Filter by budget':
    max_cost=st.number_input('Maximum total spend (€)',min_value=float(price*6),max_value=200.0,value=40.0,step=1.0)
    eligible=[m for m in modes if m['lines']*price<=max_cost+1e-9]
    if not eligible:
        st.warning('No configured mode fits that budget.')
        st.stop()
    st.caption(f"{len(eligible)} configured modes fit the €{max_cost:.2f} cap. The app filters; it does not automatically recommend the most expensive one.")

labels={m['id']:f"{m['name']} · {m['status']} · €{m['lines']*price:.2f}" for m in eligible}
default_id='642_50' if game=='6/42' else '649_k22_6'
ids=[m['id'] for m in eligible]
idx=ids.index(default_id) if default_id in ids else 0
mode_id=st.selectbox('Mode',ids,index=idx,format_func=lambda x:labels[x])

draws=get_draws(game)
state=generate_mode(game,mode_id,draws,target['draw_no']);tickets=state['tickets']

m1,m2,m3,m4,m5=st.columns(5)
m1.metric('Selection pool',f"K{state['k']}")
m2.metric('Lines',len(tickets))
m3.metric('Cost',f"€{state['cost']:.2f}")
m4.metric('Status',state['status'])
m5.metric('Repeat additions',', '.join(map(str,state['additions'])) if state['additions'] else 'none')

if 'Shadow' in state['status']:
    st.warning('Shadow mode: shown for comparison and prospective tracking, not promoted to production.')
if 'high spend' in state['status']:
    st.warning('High-spend analytical mode. It is not the baseline play size.')

st.markdown(f"### Current K{state['k']} pool")
st.code('  '.join(f'{x:02d}' for x in state['pool']),language=None)

with st.expander('Number scores, ranks and gaps'):
    d=state['diagnostics'].copy();d.score=d.score.round(3)
    st.dataframe(d,use_container_width=True,hide_index=True)

st.markdown('### Tickets')
tf=ticket_frame(tickets);st.dataframe(tf,use_container_width=True,hide_index=True,height=540)

a,b,c=st.columns(3)
a.download_button('Download CSV',tf.to_csv(index=False).encode(),file_name=f'{game.replace("/","")}_{mode_id}.csv',mime='text/csv',use_container_width=True)
b.download_button('Download text','\n'.join(' '.join(f'{x:02d}' for x in t) for t in tickets).encode(),file_name=f'{game.replace("/","")}_{mode_id}.txt',mime='text/plain',use_container_width=True)

model_version=MODEL_642 if game=='6/42' else MODEL_649
wheel_version=WHEEL_642 if game=='6/42' else WHEEL_649
if c.button('Stage as prospective play',use_container_width=True):
    play=make_play(game,mode_id,target,state['pool'],state['additions'],tickets,state['cost'],model_version,APP_VERSION)
    play['wheel_version']=wheel_version
    append_session(play,st.session_state)
    st.success('Staged prospectively in this session. Open Prospective Ledger to review/persist it.')

st.caption(f"Model: {model_version} · Wheel: {wheel_version} · App: {APP_VERSION}")
caveat()
