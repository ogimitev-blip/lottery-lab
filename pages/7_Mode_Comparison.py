import math
import pandas as pd
import streamlit as st
from lottery.ui import setup_page,hero,caveat
from lottery.data import get_draws,next_draw_info
from lottery.modes import modes_for_game,generate_mode
from lottery.wheels import line_price

setup_page('Mode Comparison · Lottery Lab','⚖️')
hero('Mode Comparison','Compare configured play modes without turning the comparison into a recommendation.')

game=st.segmented_control('Game',['6/42','6/49'],default='6/42')
target=next_draw_info(game);price=line_price(game,target['draw_no']);modes=modes_for_game(game)
ids=[m['id'] for m in modes];names={m['id']:m['name'] for m in modes}
default=ids[:min(5,len(ids))]
selected=st.multiselect('Modes to compare',ids,default=default,format_func=lambda x:names[x],max_selections=10)
if not selected:
    st.info('Select at least one mode.');caveat();st.stop()

draws=get_draws(game);rows=[]
N=42 if game=='6/42' else 49
for mid in selected:
    s=generate_mode(game,mid,draws,target['draw_no']);L=len(s['tickets']);K=s['k'];m=s['mode']
    rows.append({
        'mode':s['label'],'status':s['status'],'K':K,'lines':L,'cost_eur':s['cost'],
        'guarantee':m.get('guarantee','—'),
        'conversion':s.get('conversion_version','custom/benchmark wheel'),
        'jackpot_1_in':math.comb(N,6)/L,
        'P6_given_pool6':L/math.comb(K,6),
        'current_pool':" ".join(map(str,s['pool']))
    })
df=pd.DataFrame(rows)
st.dataframe(df.style.format({'cost_eur':'€{:.2f}','jackpot_1_in':'1 in {:,.0f}','P6_given_pool6':'{:.4%}'}),use_container_width=True,hide_index=True)

st.caption(f"Target draw #{target['draw_no']} ({target['date']}); line price €{price:.2f}. At fixed L distinct lines, raw jackpot probability is L / C({N},6).")
st.info('Official System 104 (6/42) and System 118 (6/49) are the exact-system challengers retained from the v10 robustness work. They are available for generation, but neither is presented as statistically proven superior after multiple-comparison correction.')
caveat()
