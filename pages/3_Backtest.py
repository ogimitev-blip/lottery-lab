import streamlit as st
import pandas as pd
from lottery.ui import setup_page,hero,caveat
from lottery.data import get_draws,load_custom_wheel,load_system36
from lottery.backtest import walk_forward_642,summarize_backtest
from lottery.wheels import cost

setup_page('Backtest · Lottery Lab','📈')
hero('Walk-forward Backtest','Each 6/42 target draw uses only older draws. Selection and ticket conversion remain separate.')

draws=get_draws('6/42'); dt=tuple(map(tuple,draws)); custom=tuple(map(tuple,load_custom_wheel()))
n=st.select_slider('K28 custom system size',options=[18,30,50,80,130],value=50)
bt=walk_forward_642(dt,custom,50,n); s=summarize_backtest(bt)
m=st.columns(6)
m[0].metric('OOS draws',s['draws']);m[1].metric('Cost/draw',f"€{cost('6/42',n):.2f}");m[2].metric('K28 6/6',f"{s['pool_p6']:.1%}");m[3].metric('Ticket 3+',f"{s['ticket_p3plus']:.1%}");m[4].metric('Ticket 4+',f"{s['ticket_p4plus']:.1%}");m[5].metric('Ticket 5+',f"{s['ticket_p5plus']:.2%}")
dist=pd.DataFrame({'hits':range(1,7),'pool_draws':[int((bt.pool_hits==h).sum()) for h in range(1,7)],'best_ticket_draws':[int((bt.best_ticket_hits==h).sum()) for h in range(1,7)]})
st.markdown('### Selection vs conversion');st.bar_chart(dist.set_index('hits'),height=380)
if n==50:
    off=walk_forward_642(dt,tuple(map(tuple,load_system36())),50,50);a=summarize_backtest(bt);b=summarize_backtest(off)
    cmp=pd.DataFrame([{'system':'Custom K28-50','P3+':a['ticket_p3plus'],'P4+':a['ticket_p4plus'],'P5+':a['ticket_p5plus'],'P6':a['ticket_p6']},{'system':'Official System 36','P3+':b['ticket_p3plus'],'P4+':b['ticket_p4plus'],'P5+':b['ticket_p5plus'],'P6':b['ticket_p6']}])
    st.markdown('### Custom K28-50 vs official System 36');st.dataframe(cmp.style.format({'P3+':'{:.2%}','P4+':'{:.2%}','P5+':'{:.2%}','P6':'{:.4%}'}),use_container_width=True,hide_index=True)
with st.expander('Per-draw OOS results'):
    st.dataframe(bt[['draw_index_newest_first','actual','pool_hits','best_ticket_hits','n_3plus','n_4plus','n_5plus','n_6']],use_container_width=True,hide_index=True,height=500)
caveat()
