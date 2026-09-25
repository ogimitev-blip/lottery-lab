import pandas as pd
import streamlit as st

from lottery.ui import setup_page,hero,caveat
from lottery.data import get_draws,next_draw_info,validate_history
from lottery.modes import modes_for_game,generate_mode
from lottery.wheels import ticket_frame,line_price
from lottery.ledger import make_play,append_session
from lottery.crowd import latest_crowd_snapshot,score_ticket_frame,anti_crowd_remap,constrained_anti_crowd_remap,snapshot_summary
from lottery.version import APP_VERSION,MODEL_642,MODEL_649,WHEEL_642,WHEEL_649

setup_page('Generator · Lottery Lab','🎟️')
hero('Ticket & System Generator','Choose the game, spending envelope and mode. Selection, conversion and crowd-sharing risk are kept as separate layers.')

game=st.segmented_control('Game',['6/42','6/49'],default='6/42')
target=next_draw_info(game)
price=line_price(game,target['draw_no'])

errors,warnings=validate_history(game)
if errors: st.error('Data-quality errors detected: '+'; '.join(errors[:3]))
if warnings: st.warning('Data-quality note: '+'; '.join(warnings[:2]))

c1,c2,c3=st.columns([1,1,1])
c1.metric('Target draw',f"#{target['draw_no']}")
c2.metric('Draw date',target['date'])
c3.metric('Line price',f"€{price:.2f}",delta='Special draw' if game=='6/49' and price>0.90 else None)

modes=modes_for_game(game)
input_mode=st.radio('How do you want to choose?',['Choose mode','Filter by budget'],horizontal=True)
eligible=modes
if input_mode=='Filter by budget':
    min_lines=min(m['lines'] for m in modes)
    max_cost=st.number_input('Maximum total spend (€)',min_value=float(price*min_lines),max_value=250.0,value=40.0,step=1.0)
    eligible=[m for m in modes if m['lines']*price<=max_cost+1e-9]
    if not eligible:
        st.warning('No configured mode fits that budget.'); st.stop()
    st.caption(f"{len(eligible)} configured modes fit the €{max_cost:.2f} cap. Filtering does not imply a recommendation to spend up to the cap.")

labels={m['id']:f"{m['name']} · {m['status']} · €{m['lines']*price:.2f}" for m in eligible}
default_id='642_50' if game=='6/42' else '649_k22_6'
ids=[m['id'] for m in eligible]
idx=ids.index(default_id) if default_id in ids else 0
mode_id=st.selectbox('Mode',ids,index=idx,format_func=lambda x:labels[x])

draws=get_draws(game)
state=generate_mode(game,mode_id,draws,target['draw_no'])
base_tickets=list(state['tickets'])
tickets=list(base_tickets)
mode=state['mode']

crowd=latest_crowd_snapshot(game)
crowd_summary=snapshot_summary(crowd)
anti_crowd=False
anti_meta=None

if not crowd.empty:
    anti_crowd=st.toggle(
        'Experimental anti-crowd conversion',
        value=False,
        help='Keeps the selected K-number pool and the wheel incidence structure, but relabels positions so less-played BST numbers receive more ticket exposure. This targets prize-sharing risk, not draw probability.'
    )
    if anti_crowd:
        tickets,anti_map,anti_meta=anti_crowd_remap(state['pool'],base_tickets,crowd)
        state['tickets']=tickets
        st.info(
            f"Anti-crowd remap is ON using BST played-number snapshot draw #{crowd_summary['draw']} "
            f"({crowd_summary['date']}). The selected pool, line count and combinatorial coverage structure are unchanged."
        )

base_crowd=score_ticket_frame(base_tickets,crowd) if not crowd.empty else pd.DataFrame()
ticket_crowd=score_ticket_frame(tickets,crowd) if not crowd.empty else pd.DataFrame()

cols=st.columns(6)
cols[0].metric('Selection pool',f"K{state['k']}")
cols[1].metric('Lines',len(tickets))
cols[2].metric('Cost',f"€{state['cost']:.2f}")
cols[3].metric('Status',state['status'])
cols[4].metric('Repeat additions',', '.join(map(str,state['additions'])) if state['additions'] else 'none')
if not ticket_crowd.empty:
    avg=float(ticket_crowd.crowd_index.mean())
    delta=None
    if anti_crowd and not base_crowd.empty:
        delta=f"{avg-float(base_crowd.crowd_index.mean()):+.1f}"
    cols[5].metric('Avg crowd index',f"{avg:.1f}",delta=delta,delta_color='inverse')
else:
    cols[5].metric('Avg crowd index','—')

if 'Shadow' in state['status']:
    st.warning('Shadow mode: shown for comparison and prospective tracking, not promoted to production.')
if 'high spend' in state['status']:
    st.warning('High-spend analytical mode. It is not the baseline play size.')
if mode.get('kind') in ('exact','exact_curated'):
    st.info(
        f"Exact published reduced system #{mode['system_no']} · K{mode['k']} · {mode['lines']} lines · "
        f"published guarantee {mode.get('guarantee','—')}. It remains a challenger/benchmark rather than a proven replacement for the production architecture."
    )
    st.caption(state['architecture_note'])
    if anti_crowd:
        st.warning('Anti-crowd relabeling replaces the normal model/exposure position mapping for this generated play. The published guarantee is invariant to relabeling, but this is an experimental conversion variant.')

st.markdown(f"### Current K{state['k']} selection")
st.code('  '.join(f'{x:02d}' for x in state['pool']),language=None)

with st.expander('Number scores, ranks and gaps'):
    d=state['diagnostics'].copy(); d.score=d.score.round(3)
    if not crowd.empty:
        pop=crowd[['number','played_count','played_vs_mean','popularity_rank']].copy()
        d=d.merge(pop,on='number',how='left')
    st.dataframe(d,use_container_width=True,hide_index=True)

if mode.get('kind') in ('exact','exact_curated') and 'position_mapping' in state:
    with st.expander('Exact-system position mapping'):
        st.caption('Default exact-system mapping assigns the strongest model numbers to the most-exposed published positions. Anti-crowd mode can then relabel those positions using player-popularity data.')
        st.dataframe(state['position_mapping'],use_container_width=True,hide_index=True)

if anti_crowd and anti_meta is not None:
    with st.expander('Anti-crowd relabeling'):
        st.dataframe(anti_meta,use_container_width=True,hide_index=True)

st.markdown('### Tickets')
tf=ticket_frame(tickets)
if not ticket_crowd.empty:
    extra=ticket_crowd.drop(columns=['line']).reset_index(drop=True)
    tf=pd.concat([tf.reset_index(drop=True),extra],axis=1)
    tf['crowd_index']=tf['crowd_index'].round(1)
st.dataframe(tf,use_container_width=True,hide_index=True,height=540)

if not crowd.empty:
    st.caption(
        f"Crowd index uses BST marginal played-number counts from snapshot #{crowd_summary['draw']} ({crowd_summary['date']}); "
        "100 ≈ average per-number popularity, lower is less popular. It is a proxy for sharing risk, not an estimate of draw probability or exact ticket duplication."
    )

a,b,c=st.columns(3)
a.download_button('Download CSV',tf.to_csv(index=False).encode(),file_name=f'{game.replace("/","")}_{mode_id}.csv',mime='text/csv',use_container_width=True)
b.download_button('Download text','\n'.join(' '.join(f'{x:02d}' for x in t) for t in tickets).encode(),file_name=f'{game.replace("/","")}_{mode_id}.txt',mime='text/plain',use_container_width=True)

model_version=MODEL_642 if game=='6/42' else MODEL_649
default_wheel=WHEEL_642 if game=='6/42' else WHEEL_649
conversion_version=state.get('conversion_version',default_wheel)
if anti_crowd:
    conversion_version += ' + anti-crowd relabel v1'

if c.button('Stage as prospective play',use_container_width=True):
    play=make_play(game,mode_id,target,state['pool'],state['additions'],tickets,state['cost'],model_version,APP_VERSION)
    play['wheel_version']=conversion_version
    play['mode_status']=state['status']
    play['anti_crowd']=bool(anti_crowd)
    if not crowd.empty:
        play['crowd_snapshot_draw']=crowd_summary['draw']
        play['crowd_snapshot_date']=crowd_summary['date']
        play['avg_crowd_index']=float(ticket_crowd.crowd_index.mean())
    if mode.get('kind') in ('exact','exact_curated'):
        play['system_no']=mode['system_no']
        play['mapping_method']=state['mapping_method']
    append_session(play,st.session_state)
    st.success('Staged prospectively in this session. Open Prospective Ledger to review/persist it.')

st.caption(f"Model: {model_version} · Conversion: {conversion_version} · App: {APP_VERSION}")
caveat()
