import pandas as pd
import streamlit as st

from lottery.ui import setup_page,hero,caveat
from lottery.data import get_draws,latest_stored_info,load_research_archive
from lottery.modes import modes_for_game
from lottery.crowd import load_crowd_history
from lottery.research_backtests import (
    backtest_mode,summarize_mode_backtest,
    backtest_crowd_layer,summarize_crowd_backtest,
)
from lottery.historylab import compare_history_depth,summarize_depth

setup_page('Research Backtests · Lottery Lab','🧪')
hero('Research Backtests','Leakage-free tests for ticket modes, the anti-crowd layer, and deeper history. Research results do not automatically change production.')

tab1,tab2,tab3=st.tabs(['Mode backtest','Anti-crowd backtest','History depth'])

with tab1:
    game=st.segmented_control('Game',['6/42','6/49'],default='6/49',key='bt_game')
    modes=modes_for_game(game)
    ids=[m['id'] for m in modes]
    names={m['id']:m['name'] for m in modes}
    default='649_k22_4' if game=='6/49' else '642_18'
    mid=st.selectbox('Mode',ids,index=ids.index(default) if default in ids else 0,format_func=lambda x:names[x])
    window=st.select_slider('OOS targets',options=[25,50,100,150],value=50)
    draws=get_draws(game)
    with st.spinner('Running walk-forward backtest...'):
        bt=backtest_mode(game,mid,draws,max_targets=window,min_history=50)
        s=summarize_mode_backtest(bt)
    m=st.columns(6)
    m[0].metric('OOS draws',s.get('draws',0))
    m[1].metric('Mean pool hits',f"{s.get('pool_mean',0):.3f}")
    m[2].metric('Pool P(5+)',f"{s.get('pool_p5plus',0):.1%}")
    m[3].metric('Best-ticket P(3+)',f"{s.get('p3plus',0):.1%}")
    m[4].metric('Best-ticket P(4+)',f"{s.get('p4plus',0):.1%}")
    m[5].metric('Best-ticket P(5+)',f"{s.get('p5plus',0):.2%}")
    if not bt.empty:
        st.line_chart(bt[['pool_hits','best_hits']],height=350)
        with st.expander('Per-draw results'):
            st.dataframe(bt,use_container_width=True,hide_index=True,height=450)

with tab2:
    game=st.segmented_control('Game',['6/42','6/49'],default='6/49',key='crowd_game')
    modes=modes_for_game(game)
    # Prefer low/medium custom modes; exact systems are allowed but can be slower.
    ids=[m['id'] for m in modes]
    names={m['id']:m['name'] for m in modes}
    default='649_k22_4' if game=='6/49' else '642_18'
    mid=st.selectbox('Mode to test',ids,index=ids.index(default) if default in ids else 0,format_func=lambda x:names[x],key='crowd_mode')
    draws=get_draws(game)
    crowd=load_crowd_history(game)
    latest=latest_stored_info(game)
    bt=backtest_crowd_layer(game,mid,draws,crowd,latest['draw_no'],max_targets=100,min_history=50)
    s=summarize_crowd_backtest(bt)
    if not s:
        st.info('No strictly pre-target crowd snapshot is available yet for this test.')
    else:
        st.caption('Only targets after an already-known crowd snapshot are included; the crowd layer never uses a future snapshot.')
        m=st.columns(6)
        m[0].metric('Eligible draws',s['draws'])
        m[1].metric('Avg crowd index · base',f"{s['base_crowd']:.1f}")
        m[2].metric('Avg crowd index · anti',f"{s['anti_crowd']:.1f}",delta=f"{-100*s['crowd_reduction_pct']:.1f}%")
        m[3].metric('P(3+) · base',f"{s['base_p3plus']:.1%}")
        m[4].metric('P(3+) · anti',f"{s['anti_p3plus']:.1%}")
        m[5].metric('Better / tie / worse',f"{s['anti_better']} / {s['ties']} / {s['base_better']}")
        st.dataframe(bt,use_container_width=True,hide_index=True,height=420)
        st.warning('This can test whether anti-crowd relabeling reduces the popularity proxy without badly damaging ticket conversion. It cannot yet test actual prize-sharing benefit because BST does not publish exact six-number ticket popularity for every ticket.')

with tab3:
    game=st.segmented_control('Game',['6/42','6/49'],default='6/42',key='hist_game')
    draws=get_draws(game)
    _,archive=load_research_archive(game)
    window=st.select_slider('OOS targets',options=[50,100,150],value=150,key='hist_window')
    bt=compare_history_depth(game,draws,archive,max_targets=window,min_history=50)
    s=summarize_depth(bt)
    m=st.columns(6)
    m[0].metric('OOS draws',s.get('draws',0))
    m[1].metric('Mean hits · baseline',f"{s.get('baseline_mean',0):.3f}")
    m[2].metric('Mean hits · extended',f"{s.get('extended_mean',0):.3f}")
    m[3].metric('P(5+) · baseline',f"{s.get('baseline_p5',0):.1%}")
    m[4].metric('P(5+) · extended',f"{s.get('extended_p5',0):.1%}")
    m[5].metric('Extended better / tie / worse',f"{s.get('extended_wins',0)} / {s.get('ties',0)} / {s.get('baseline_wins',0)}")
    st.dataframe(bt,use_container_width=True,hide_index=True,height=420)
    st.warning('Older-history results remain research-only until they outperform robustly across multiple windows; they are not silently fed into production.')

caveat()
