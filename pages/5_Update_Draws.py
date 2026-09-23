import streamlit as st
from datetime import date
from lottery.ui import setup_page,hero,caveat
from lottery.data import load_draws_df,next_draw_info,load_sync_state
from lottery.admin import parse_numbers,updated_csv,github_commit_draw,password_ok

setup_page('Update Draws · Lottery Lab','➕')
hero('Update Draws','Official results are now synced automatically. Manual entry remains available as an immediate fallback.')

game=st.segmented_control('Game',['6/42','6/49'],default='6/42')
target=next_draw_info(game);state=load_sync_state()[game]
a,b,c=st.columns(3)
a.metric('Stored through draw',f"#{state['latest_draw_no']}")
b.metric('Stored through date',state['latest_date'])
c.metric('Expected next draw',f"#{target['draw_no']} · {target['date']}")

st.success('A scheduled ChatGPT sync checks official BST result pages after Thursday and Sunday draws. When a newer result is fully verified, it updates the GitHub draw data and payout metadata; Streamlit then redeploys.')

with st.expander('Manual fallback / immediate use'):
    draw_no=st.number_input('Draw number',min_value=1,value=int(target['draw_no']),step=1)
    draw_date=st.date_input('Draw date',value=date.fromisoformat(target['date'])).isoformat()
    raw=st.text_input('Six drawn numbers',placeholder='e.g. 4 12 14 16 20 42')
    nums=None
    if raw.strip():
        try:
            nums=parse_numbers(raw,game);st.success('Validated: '+'  '.join(f'{n:02d}' for n in nums))
        except ValueError as e:st.error(str(e))
    if nums:
        c1,c2=st.columns(2)
        if c1.button('Use in this session',use_container_width=True):
            key=f'session_draws_{game}';items=st.session_state.setdefault(key,[])
            if not items or items[0]['numbers']!=nums:items.insert(0,{'date':draw_date,'numbers':nums,'draw_no':int(draw_no)})
            st.success('Added for this browser session. Generator and Past Draws use it immediately.')
        df=load_draws_df(game)
        try:
            body=updated_csv(df,int(draw_no),draw_date,nums)
            c2.download_button('Download updated CSV',body.encode(),file_name='draws_642.csv' if game=='6/42' else 'draws_649.csv',mime='text/csv',use_container_width=True)
        except ValueError as e:st.info(str(e))

    has_admin='ADMIN_PASSWORD' in st.secrets and 'GITHUB_TOKEN' in st.secrets
    if has_admin and nums:
        pwd=st.text_input('Admin password',type='password')
        if st.button('Commit manual result to GitHub',type='primary'):
            if not password_ok(pwd,st.secrets['ADMIN_PASSWORD']):st.error('Incorrect admin password.')
            else:
                try:
                    url=github_commit_draw(game,int(draw_no),draw_date,nums,st.secrets['GITHUB_TOKEN'])
                    st.success('Committed. Automatic sync will reconcile its state/official payout metadata on the next run.')
                    st.link_button('Open commit',url)
                    load_draws_df.clear()
                except Exception as e:st.error(f'GitHub update failed: {e}')
    elif not has_admin:
        st.caption('Optional direct manual GitHub commits require ADMIN_PASSWORD + GITHUB_TOKEN in Streamlit Secrets. The scheduled official sync is separate and does not require these app secrets.')

with st.expander('Current newest stored row'):
    st.write(load_draws_df(game).iloc[0].to_dict())

caveat()
