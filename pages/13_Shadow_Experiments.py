import pandas as pd
import streamlit as st

from lottery.ui import setup_page,hero,caveat
from lottery.shadow import score_all_shadows,read_shadow_rows,summarize_shadow_pairs,shadow_research_scoreboard,shadow_cycle_health,PROMOTION_MIN_DRAWS,PROMOTION_PREFERRED_DRAWS

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


st.markdown('### Shadow cycle health')
cycle=shadow_cycle_health(df.to_dict('records'))
if len(cycle):
    st.dataframe(
        cycle.rename(columns={
            'latest_scored_draw':'Latest scored draw',
            'next_shadow_draw':'Next frozen draw',
            'target_date':'Target date',
            'frozen_variants':'Frozen variants',
            'expected_variants':'Expected variants',
            'freeze_before_target':'Frozen before target',
            'cycle_status':'Cycle status',
        }),
        use_container_width=True,hide_index=True
    )
    bad=cycle[cycle.cycle_status!='READY']
    if len(bad):
        st.warning('At least one game does not currently have a complete, timely next shadow batch.')
    else:
        st.success('Both games have a complete prospective batch frozen before the target draw.')


st.markdown('### Frozen ledger')
show_cols=[
    'game','target_draw_no','target_date','label','mode_id','crowd_strength',
    'notional_stake_eur','status','pool_hits','best_ticket_hits','selection_misses','conversion_misses','conversion_capture_pct',
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

if len(scored):
    st.markdown('### Selection vs conversion attribution')
    latest_scored=int(pd.to_numeric(scored.target_draw_no,errors='coerce').max())
    attr=scored[pd.to_numeric(scored.target_draw_no,errors='coerce')==latest_scored].copy()
    attr['conversion_capture_pct']=pd.to_numeric(attr['conversion_capture_pct'],errors='coerce').round(1)
    st.dataframe(
        attr[[
            'game','target_draw_no','label','mode_id','crowd_strength',
            'pool_hits','selection_misses','best_ticket_hits','conversion_misses',
            'conversion_capture_pct','winning_lines_3plus'
        ]].rename(columns={
            'target_draw_no':'Draw',
            'crowd_strength':'Crowd strength',
            'pool_hits':'Pool hits',
            'selection_misses':'Selection misses',
            'best_ticket_hits':'Best ticket hits',
            'conversion_misses':'Conversion misses',
            'conversion_capture_pct':'Pool-hit capture %',
            'winning_lines_3plus':'3+ lines',
        }),
        use_container_width=True,hide_index=True
    )
    st.caption(
        'Attribution identity: 6 winning numbers = selection misses + conversion misses + best-ticket hits. '
        'For baseline and anti-crowd variants of the same mode the pool is identical, so any same-draw difference '
        'between them is conversion-layer behavior, not selection.'
    )

st.markdown('### Research scoreboard')
scoreboard=shadow_research_scoreboard(df.to_dict('records'))
if scoreboard.empty:
    st.info('The scoreboard will populate after the first completed prospective baseline-vs-variant draw.')
else:
    sb=scoreboard.copy()
    sb['crowd_strength_pct']=(100*sb.pop('crowd_strength')).round().astype(int)
    for col in [
        'nondegradation_rate_pct','nondegradation_ci95_lo_pct','nondegradation_ci95_hi_pct',
        'crowd_reduction_positive_pct','avg_crowd_reduction_pct','median_crowd_reduction_pct'
    ]:
        sb[col]=pd.to_numeric(sb[col],errors='coerce').round(1)
    sb['cumulative_payout_delta_eur']=pd.to_numeric(sb['cumulative_payout_delta_eur'],errors='coerce').round(2)
    st.dataframe(
        sb[[
            'game','mode_id','variant_label','crowd_strength_pct','prospective_draws','evidence_maturity',
            'best_hit_wins','best_hit_ties','best_hit_losses','best_hit_net',
            'nondegradation_rate_pct','nondegradation_ci95_lo_pct','nondegradation_ci95_hi_pct',
            'p3_gains','p3_same','p3_losses','p3_net',
            'crowd_reduction_positive_pct','avg_crowd_reduction_pct',
            'cumulative_payout_delta_eur'
        ]].rename(columns={
            'crowd_strength_pct':'Crowd strength %',
            'prospective_draws':'Draws',
            'evidence_maturity':'Evidence maturity',
            'best_hit_wins':'Best-hit wins',
            'best_hit_ties':'Best-hit ties',
            'best_hit_losses':'Best-hit losses',
            'best_hit_net':'Best-hit net',
            'nondegradation_rate_pct':'Non-degradation %',
            'nondegradation_ci95_lo_pct':'95% CI low',
            'nondegradation_ci95_hi_pct':'95% CI high',
            'p3_gains':'3+ gains',
            'p3_same':'3+ same',
            'p3_losses':'3+ losses',
            'p3_net':'3+ net',
            'crowd_reduction_positive_pct':'Crowd reduction draws %',
            'avg_crowd_reduction_pct':'Avg crowd reduction %',
            'cumulative_payout_delta_eur':'Cumulative payout Δ €',
        }),
        use_container_width=True,hide_index=True
    )
    st.caption(
        'Wins/ties/losses are same-draw paired comparisons against the baseline. '
        'The 95% interval is for the non-degradation rate of best-ticket hits; it is descriptive, '
        'not a claim that lottery outcomes are predictable.'
    )

st.markdown('### Forward promotion gate')
gate=summarize_shadow_pairs(df.to_dict('records'))
if gate.empty:
    st.info(
        f'No completed prospective baseline-vs-variant pairs yet. '
        f'The first formal review starts after {PROMOTION_MIN_DRAWS} scored draws per mode; '
        f'{PROMOTION_PREFERRED_DRAWS}+ is the preferred promotion-review sample.'
    )
else:
    gate_show=gate.copy()
    gate_show['crowd_strength_pct']=(100*gate_show.pop('crowd_strength')).round().astype(int)
    gate_show['avg_crowd_reduction_pct']=pd.to_numeric(gate_show['avg_crowd_reduction_pct'],errors='coerce').round(2)
    gate_show['base_3plus_rate_pct']=gate_show['base_3plus_rate_pct'].round(1)
    gate_show['variant_3plus_rate_pct']=gate_show['variant_3plus_rate_pct'].round(1)
    gate_show['delta_3plus_pp']=gate_show['delta_3plus_pp'].round(1)
    gate_show['mean_best_ticket_hit_delta']=gate_show['mean_best_ticket_hit_delta'].round(3)
    gate_show['mean_winning_lines_delta']=gate_show['mean_winning_lines_delta'].round(3)
    gate_show['cumulative_payout_delta_eur']=pd.to_numeric(gate_show['cumulative_payout_delta_eur'],errors='coerce').round(2)
    st.dataframe(
        gate_show[[
            'game','mode_id','variant_label','crowd_strength_pct','prospective_draws','sample_gate',
            'draws_to_min_review','draws_to_preferred','avg_crowd_reduction_pct',
            'base_3plus_rate_pct','variant_3plus_rate_pct','delta_3plus_pp',
            'mean_best_ticket_hit_delta','mean_winning_lines_delta','cumulative_payout_delta_eur'
        ]].rename(columns={
            'crowd_strength_pct':'Crowd strength %',
            'prospective_draws':'Prospective draws',
            'sample_gate':'Gate',
            'draws_to_min_review':'To 30-draw review',
            'draws_to_preferred':'To 50-draw review',
            'avg_crowd_reduction_pct':'Avg crowd reduction %',
            'base_3plus_rate_pct':'Base P(3+) %',
            'variant_3plus_rate_pct':'Variant P(3+) %',
            'delta_3plus_pp':'Δ P(3+) pp',
            'mean_best_ticket_hit_delta':'Mean Δ best hits',
            'mean_winning_lines_delta':'Mean Δ 3+ lines',
            'cumulative_payout_delta_eur':'Cumulative payout Δ €',
        }),
        use_container_width=True,hide_index=True
    )

st.caption(
    'Gate logic is pre-committed: under 30 paired prospective draws = accumulate only; '
    '30–49 = interim review only; at 50+ a variant can become eligible for promotion review '
    'only if it has reduced crowd exposure without lowering paired best-ticket hits or 3+ draw frequency. '
    'Payout is shown as secondary evidence and never promotes a variant by itself.'
)

with st.expander('Pre-registered design'):
    st.write('6/49 K22-4: baseline vs constrained 10%.')
    st.write('6/49 K22-6: baseline vs constrained 30%.')
    st.write('6/42 K28-18, K28-30 and K28-50: baseline vs constrained 10%.')
    st.write('Exact tickets, pools, versions and crowd snapshot are frozen before the target draw.')

st.caption('Shadow ROI is notional and is not a recommendation to spend.')
caveat()
