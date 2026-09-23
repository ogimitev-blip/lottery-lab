import json
import pandas as pd
import streamlit as st
from lottery.ui import setup_page,hero,caveat
from lottery.ledger import all_plays,score_play,github_append_play
from lottery.admin import password_ok

setup_page('Prospective Ledger · Lottery Lab','🧾')
hero('Prospective Ledger','Freeze plays before the draw, then score them automatically after the official result is synced.')

plays=all_plays(st.session_state)
if not plays:
    st.info('No prospective plays yet. Generate a mode and click “Stage as prospective play”.')
    caveat();st.stop()

scored=[score_play(p) for p in sorted(plays,key=lambda x:x['created_at'],reverse=True)]
rows=[]
for p in scored:
    rows.append({
        'created_at':p['created_at'][:19].replace('T',' '),
        'game':p['game'],'mode':p['mode_id'],'target_draw':p['target_draw_no'],'target_date':p['target_date'],
        'stake_eur':p['stake_eur'],'status':p['status'],
        'pool_hits':p.get('pool_hits'),'best_ticket':p.get('best_ticket_hits'),
        'payout_eur':p.get('payout_eur'),'roi':p.get('roi')
    })
df=pd.DataFrame(rows)
fmt={'stake_eur':'€{:.2f}','payout_eur':'€{:.2f}','roi':'{:.1%}'}
st.dataframe(df.style.format(fmt,na_rep='—'),use_container_width=True,hide_index=True)

pending_session=st.session_state.get('prospective_plays',[])
if pending_session:
    st.markdown('### Persist staged plays')
    st.write('Session-staged plays disappear when the session resets unless they are committed to the repository.')
    has_admin='ADMIN_PASSWORD' in st.secrets and 'GITHUB_TOKEN' in st.secrets
    if has_admin:
        pwd=st.text_input('Admin password',type='password')
        if st.button('Commit all staged plays to GitHub',type='primary'):
            if not password_ok(pwd,st.secrets['ADMIN_PASSWORD']):
                st.error('Incorrect admin password.')
            else:
                ok=0
                try:
                    for p in pending_session:
                        github_append_play(p,st.secrets['GITHUB_TOKEN']);ok+=1
                    st.success(f'Persisted {ok} prospective play(s). Streamlit will refresh after the repository update.')
                except Exception as e:st.error(f'Persistence failed after {ok}: {e}')
    else:
        st.warning('GitHub persistence requires the same optional ADMIN_PASSWORD + GITHUB_TOKEN Streamlit secrets used by the manual draw updater.')
        payload='\n'.join(json.dumps(p,separators=(',',':')) for p in pending_session)+'\n'
        st.download_button('Download staged ledger JSONL',payload.encode(),file_name='prospective_plays.jsonl',mime='application/x-ndjson')

with st.expander('Inspect exact frozen play'):
    ids=[p['play_id'] for p in scored]
    pid=st.selectbox('Play',ids,format_func=lambda x:next(f"{p['game']} draw {p['target_draw_no']} · {p['mode_id']} · {p['created_at'][:16]}" for p in scored if p['play_id']==x))
    p=next(p for p in scored if p['play_id']==pid)
    st.json(p,expanded=False)

caveat()
