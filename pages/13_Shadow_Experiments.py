import pandas as pd
import streamlit as st

from lottery.ui import setup_page,hero,caveat
from lottery.shadow import score_all_shadows,read_shadow_rows

setup_page('Shadow Experiments · Lottery Lab','👤')
hero('Prospective Shadow Experiments','Frozen research variants are scored after each draw. Actual money spent is always zero.')

rows=read_shadow_rows()
if not rows:
    st.info('No shadow batch has been frozen yet.')
    caveat()
    st.stop()

df=pd.DataFrame(score_all_shadows())
pending=int((df.status=='pending').sum())
finished=int((df.status=='scored').sum())

a,b,c,d=st.columns(4)
a.metric('Frozen variants',len(df))
b.metric('Scored variants',finished)
c.metric('Pending variants',pending)
d.metric('Actual money spent','€0.00')

st.markdown('### Frozen ledger')
show_cols=[
    'game','target_draw_no','target_date','label','mode_id','crowd_strength',
    'notional_stake_eur','status','pool_hits','best_ticket_hits',
    'winning_lines_3plus','notional_payout_eur','notional_net_eur',
    'notional_roi','avg_crowd_index','optimizer_swaps'
]
show=df[[x for x in show_cols if x in df.columns]].copy()
if 'crowd_strength' in show.columns:
    show['crowd_strength_pct']=(100*show.pop('crowd_strength')).round().astype(int)
if 'notional_roi' in show.columns:
    show['notional_roi_pct']=100*show.pop('notional_roi')
st.dataframe(show,use_container_width=True,hide_index=True,height=520)

scored=df[df.status=='scored'].copy()
if len(scored):
    st.markdown('### Baseline vs crowd variants')
    pairs=[]
    for (game,draw_no,mode),g in scored.groupby(['game','target_draw_no','mode_id']):
        base=g[g.crowd_strength==0]
        variants=g[g.crowd_strength>0]
        if base.empty or variants.empty:
            continue
        b=base.iloc[0]
        for _,v in variants.iterrows():
            bp=b.get('notional_payout_eur')
            vp=v.get('notional_payout_eur')
            delta=None if pd.isna(bp) or pd.isna(vp) else float(vp)-float(bp)
            pairs.append({
                'game':game,'draw':int(draw_no),'mode':mode,
                'crowd_strength_pct':int(round(100*float(v.crowd_strength))),
                'base_best':b.get('best_ticket_hits'),'crowd_best':v.get('best_ticket_hits'),
                'base_payout_eur':bp,'crowd_payout_eur':vp,'payout_delta_eur':delta,
                'base_crowd_index':b.get('avg_crowd_index'),'crowd_index':v.get('avg_crowd_index'),
            })
    if pairs:
        pair_df=pd.DataFrame(pairs)
        st.dataframe(pair_df,use_container_width=True,hide_index=True)

with st.expander('Pre-registered design'):
    st.write('6/49 K22-4: baseline vs constrained 10%.')
    st.write('6/49 K22-6: baseline vs constrained 30%.')
    st.write('6/42 K28-18, K28-30 and K28-50: baseline vs constrained 10%.')
    st.write('Exact tickets, pools, versions and crowd snapshot are frozen before the target draw.')

st.caption('Shadow ROI is notional and is not a recommendation to spend.')
caveat()
