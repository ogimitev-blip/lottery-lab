import pandas as pd
import streamlit as st
from datetime import date

from lottery.ui import setup_page,hero,caveat
from lottery.data import load_draws_df,next_draw_info,load_sync_state
from lottery.admin import (
    parse_numbers,normalize_history_frame,validate_history_frame,history_csv,
    github_replace_history,password_ok,
)

setup_page('Draw Database · Lottery Lab','🗃️')
hero('Draw Database','View every stored draw, inspect duplicate warnings, add new draws, correct old rows, or mark erroneous rows for deletion.')

game=st.segmented_control('Game',['6/42','6/49'],default='6/42')
target=next_draw_info(game)
state=load_sync_state()[game]

# Keep an editable working copy per game in this browser session.
work_key=f'history_work_{game}'
version_key=f'history_editor_version_{game}'
if work_key not in st.session_state:
    st.session_state[work_key]=normalize_history_frame(load_draws_df(game),game)
if version_key not in st.session_state:
    st.session_state[version_key]=0

c1,c2,c3=st.columns(3)
c1.metric('Stored through draw',f"#{state['latest_draw_no']}")
c2.metric('Stored through date',state['latest_date'])
c3.metric('Expected next draw',f"#{target['draw_no']} · {target['date']}")

current=st.session_state[work_key].copy()
normalized,errors,warnings,dup_groups=validate_history_frame(current,game)

st.markdown('### Data-quality check')
if errors:
    st.error('Blocking validation error(s):\n\n- '+'\n- '.join(errors[:12]))
else:
    st.success('No blocking row-format errors in the current working copy.')

if dup_groups:
    st.warning(f'{len(dup_groups)} repeated six-number result group(s) found. These are shown below so you can inspect the exact rows.')
    dup_rows=[]
    for group_no,(nums,idxs) in enumerate(dup_groups,1):
        for idx in idxs:
            r=normalized.loc[idx]
            dup_rows.append({
                'duplicate_group':group_no,
                'stored_row':int(idx)+1,
                'draw_no':None if pd.isna(r['draw_no']) else int(r['draw_no']),
                'date':None if pd.isna(r['date']) else str(r['date']),
                'numbers':' '.join(str(int(r[f'n{i}'])) for i in range(1,7)),
            })
    st.dataframe(pd.DataFrame(dup_rows),use_container_width=True,hide_index=True)

    st.markdown('#### Quick duplicate correction')
    st.caption('Edit one of the repeated rows here or tick Delete. Changes are applied to the working table only until you save them permanently.')
    quick=[]
    for group_no,(nums,idxs) in enumerate(dup_groups,1):
        for idx in idxs:
            r=normalized.loc[idx]
            quick.append({
                'Delete':False,
                'duplicate_group':group_no,
                'stored_row':int(idx)+1,
                '_source_index':int(idx),
                'draw_no':None if pd.isna(r['draw_no']) else int(r['draw_no']),
                'date':None if pd.isna(r['date']) else str(r['date']),
                **{f'n{i}':int(r[f'n{i}']) for i in range(1,7)},
            })
    quick_df=pd.DataFrame(quick)
    quick_edit=st.data_editor(
        quick_df,
        key=f'quick_dup_{game}_{st.session_state[version_key]}',
        use_container_width=True,
        hide_index=True,
        disabled=['duplicate_group','stored_row','_source_index'],
        column_config={
            'Delete':st.column_config.CheckboxColumn('Delete'),
            'duplicate_group':st.column_config.NumberColumn('Group',format='%d'),
            'stored_row':st.column_config.NumberColumn('Stored row',format='%d'),
            '_source_index':None,
            'draw_no':st.column_config.NumberColumn('Draw #',min_value=1,step=1,format='%d'),
            'date':st.column_config.TextColumn('Date'),
            **{f'n{i}':st.column_config.NumberColumn(f'N{i}',min_value=1,max_value=(42 if game=='6/42' else 49),step=1,format='%d') for i in range(1,7)},
        },
    )
    if st.button('Apply duplicate corrections',use_container_width=True):
        base=st.session_state[work_key].copy()
        drop_idx=[]
        for _,rr in quick_edit.iterrows():
            src=int(rr['_source_index'])
            if bool(rr.get('Delete',False)):
                drop_idx.append(src)
                continue
            for col in ['draw_no','date','n1','n2','n3','n4','n5','n6']:
                base.at[src,col]=rr[col]
        if drop_idx:
            base=base.drop(index=drop_idx)
        base=base.reset_index(drop=True)
        checked,qerr,qwarn,_=validate_history_frame(base,game)
        if qerr:
            st.error('Cannot apply duplicate correction: '+'; '.join(qerr[:10]))
        else:
            st.session_state[work_key]=checked
            st.session_state[version_key]+=1
            st.success('Duplicate correction applied to the working table.')
            st.rerun()
else:
    st.info('No repeated six-number results detected.')

if warnings and not dup_groups:
    for w in warnings[:8]: st.warning(w)

st.markdown('### Add a new draw')
with st.form(f'add_draw_{game}',clear_on_submit=True):
    a,b=st.columns(2)
    draw_no=a.number_input('Draw number',min_value=1,value=int(target['draw_no']),step=1)
    draw_date=b.date_input('Draw date',value=date.fromisoformat(target['date']))
    raw=st.text_input('Winning numbers',placeholder='Example: 4 12 14 16 20 42')
    submitted=st.form_submit_button('Add to working table',type='primary',use_container_width=True)
    if submitted:
        try:
            nums=parse_numbers(raw,game)
            base=st.session_state[work_key].copy()
            if 'draw_no' in base.columns and pd.to_numeric(base['draw_no'],errors='coerce').eq(int(draw_no)).any():
                raise ValueError(f'Draw #{int(draw_no)} is already present.')
            cols=[f'n{i}' for i in range(1,7)]
            row={'draw_no':int(draw_no),'date':draw_date.isoformat(),**{c:n for c,n in zip(cols,nums)}}
            st.session_state[work_key]=pd.concat([pd.DataFrame([row]),base],ignore_index=True)
            st.session_state[version_key]+=1
            st.success(f'Added draw #{int(draw_no)} to the working table. Review it below, then save.')
            st.rerun()
        except ValueError as e:
            st.error(str(e))

st.markdown('### Full draw history')
st.caption('Edit draw number, date, or any winning number directly. Tick **Delete** only for a row you want removed. “Stored row” is the current newest-first position in the file, not an official draw number.')

edit_base=st.session_state[work_key].copy().reset_index(drop=True)
display=edit_base.copy()
display.insert(0,'Delete',False)
display.insert(1,'Stored row',range(1,len(display)+1))

maxn=42 if game=='6/42' else 49
edited=st.data_editor(
    display,
    key=f'history_editor_{game}_{st.session_state[version_key]}',
    use_container_width=True,
    hide_index=True,
    height=650,
    disabled=['Stored row'],
    column_config={
        'Delete':st.column_config.CheckboxColumn('Delete',help='Remove this row when changes are applied.'),
        'Stored row':st.column_config.NumberColumn('Stored row',format='%d'),
        'draw_no':st.column_config.NumberColumn('Draw #',min_value=1,step=1,format='%d'),
        'date':st.column_config.TextColumn('Date',help='YYYY-MM-DD; older unknown dates may remain blank.'),
        **{f'n{i}':st.column_config.NumberColumn(f'N{i}',min_value=1,max_value=maxn,step=1,format='%d') for i in range(1,7)},
    },
)

candidate=edited.loc[~edited['Delete'].fillna(False)].drop(columns=['Delete','Stored row']).reset_index(drop=True)
candidate,edit_errors,edit_warnings,edit_dups=validate_history_frame(candidate,game)

c_apply,c_reset,c_download=st.columns(3)
if c_apply.button('Apply edits to working copy',use_container_width=True):
    if edit_errors:
        st.error('Cannot apply: '+'; '.join(edit_errors[:10]))
    else:
        st.session_state[work_key]=candidate
        st.session_state[version_key]+=1
        st.success('Edits applied to the working copy.')
        st.rerun()

if c_reset.button('Discard session edits',use_container_width=True):
    st.session_state[work_key]=normalize_history_frame(load_draws_df(game),game)
    st.session_state[version_key]+=1
    st.rerun()

try:
    candidate_csv=history_csv(candidate,game).encode()
    c_download.download_button(
        'Download corrected CSV',
        candidate_csv,
        file_name='draws_642.csv' if game=='6/42' else 'draws_649.csv',
        mime='text/csv',
        use_container_width=True,
    )
except ValueError:
    c_download.button('Download corrected CSV',disabled=True,use_container_width=True)

if edit_warnings:
    with st.expander('Warnings in the edited table'):
        for w in edit_warnings: st.warning(w)

st.markdown('### Save permanently')
has_admin='ADMIN_PASSWORD' in st.secrets and 'GITHUB_TOKEN' in st.secrets
if has_admin:
    pwd=st.text_input('Admin password',type='password',key=f'admin_pwd_{game}')
    confirm=st.checkbox('I have reviewed the edited table and want to replace the stored history for this game.',key=f'confirm_history_{game}')
    if st.button('Save working table to GitHub',type='primary',disabled=not confirm,use_container_width=True):
        working,save_errors,save_warnings,_=validate_history_frame(candidate,game)
        if save_errors:
            st.error('Cannot save: '+'; '.join(save_errors[:10]))
        elif not password_ok(pwd,st.secrets['ADMIN_PASSWORD']):
            st.error('Incorrect admin password.')
        else:
            try:
                url=github_replace_history(
                    game,working,st.secrets['GITHUB_TOKEN'],
                    message=f'Correct {game} draw database from Streamlit editor'
                )
                st.session_state[work_key]=working
                st.session_state[version_key]+=1
                load_draws_df.clear()
                st.success('Saved the currently edited table to GitHub. Streamlit will refresh from the committed database.')
                st.link_button('Open commit',url)
            except Exception as e:
                st.error(f'GitHub save failed: {e}')
else:
    st.warning('Permanent in-app editing is not enabled because this deployment has no admin GitHub secret. You can still edit, validate and download the corrected CSV. To enable Save-to-GitHub, add ADMIN_PASSWORD and a repository-scoped GITHUB_TOKEN in Streamlit Secrets.')

with st.expander('About the duplicate warning'):
    st.write('A repeated six-number set is not automatically deleted because two real lottery draws could, in principle, have the same six numbers. The app therefore shows the exact rows and lets you correct or delete one after checking the source.')

caveat()
