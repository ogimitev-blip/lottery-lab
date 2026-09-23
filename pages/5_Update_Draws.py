import pandas as pd
import streamlit as st
from datetime import date
from lottery.ui import setup_page,hero,caveat
from lottery.data import load_draws_df
from lottery.admin import parse_numbers,updated_csv,github_commit_draw,password_ok

setup_page('Update Draws · Lottery Lab','➕')
hero('Update Draws','Add the newest result for 6/42 or 6/49. Use it immediately in this browser session or persist it to GitHub.')

game=st.segmented_control('Game',['6/42','6/49'],default='6/42')
draw_date=st.date_input('Draw date',value=date.today()).isoformat()
raw=st.text_input('Six drawn numbers',placeholder='e.g. 4 12 14 16 20 42')

nums=None
if raw.strip():
    try:
        nums=parse_numbers(raw,game)
        st.success('Validated: '+'  '.join(f'{n:02d}' for n in nums))
    except ValueError as e:
        st.error(str(e))

if nums:
    c1,c2=st.columns(2)
    if c1.button('Use in this session',use_container_width=True):
        key=f'session_draws_{game}'
        items=st.session_state.setdefault(key,[])
        if not items or items[0]['numbers']!=nums:
            items.insert(0,{'date':draw_date,'numbers':nums})
        st.success('Added for this session. Generator and Past Draws will use it immediately.')

    df=load_draws_df(game)
    try:
        body=updated_csv(df,draw_date,nums)
        c2.download_button('Download updated CSV',body.encode(),file_name='draws_642.csv' if game=='6/42' else 'draws_649.csv',mime='text/csv',use_container_width=True)
    except ValueError as e:
        st.info(str(e))

st.markdown('### Permanent update')
st.write('The reliable permanent method is to commit the new row to the GitHub data file. Streamlit then redeploys automatically.')

has_admin='ADMIN_PASSWORD' in st.secrets and 'GITHUB_TOKEN' in st.secrets
if has_admin:
    pwd=st.text_input('Admin password',type='password')
    if st.button('Commit this draw to GitHub',type='primary',disabled=nums is None):
        if not password_ok(pwd,st.secrets['ADMIN_PASSWORD']):
            st.error('Incorrect admin password.')
        else:
            try:
                url=github_commit_draw(game,draw_date,nums,st.secrets['GITHUB_TOKEN'])
                st.success('Committed to GitHub. Streamlit should refresh after the repository update.')
                st.link_button('Open commit',url)
                load_draws_df.clear()
            except Exception as e:
                st.error(f'GitHub update failed: {e}')
else:
    st.warning('Direct GitHub saving is not enabled yet. Session mode and CSV download work now.')
    st.code('ADMIN_PASSWORD = "choose-a-private-password"\nGITHUB_TOKEN = "github_pat_..."',language='toml')
    st.caption('Add these only in Streamlit Community Cloud → App settings → Secrets. The token should be a fine-grained GitHub token restricted to ogimitev-blip/lottery-lab with Contents: Read and write. Never put it in the repository.')

with st.expander('Current newest stored draw'):
    d=load_draws_df(game).iloc[0]
    st.write(d.to_dict())

caveat()
