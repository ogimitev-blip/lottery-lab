import math
import numpy as np
import pandas as pd


def _esym(vals,k=6):
    e=np.zeros(k+1,dtype=float)
    e[0]=1.0
    for x in vals:
        for j in range(k,0,-1):
            e[j]+=x*e[j-1]
    return e


def _marginals(weights,k=6):
    z=_esym(weights,k)[k]
    out=[]
    for i,x in enumerate(weights):
        others=np.delete(weights,i)
        a=_esym(others,k-1)[k-1]
        out.append(x*a/z)
    return np.asarray(out)


def calibrate_fixed_number_preferences(crowd,k=6,tol=1e-12,max_iter=500):
    c=crowd.sort_values("number")
    counts=c.played_count.to_numpy(dtype=float)
    tickets=counts.sum()/k
    target=counts/tickets
    weights=target/(1-target)

    def renorm(w):
        gm=math.exp(float(np.log(w).mean()))
        return w/gm

    weights=renorm(weights)
    for it in range(max_iter):
        for i in range(len(weights)):
            others=np.delete(weights,i)
            e=_esym(others,k)
            q=target[i]
            weights[i]=q*e[k]/((1-q)*e[k-1])
        weights=renorm(weights)
        if it%5==0:
            err=float(np.max(np.abs(_marginals(weights,k)-target)))
            if err<tol:
                break

    return weights,float(tickets),target


def _combination_probability(combo,weights,k=6):
    z=_esym(weights,k)[k]
    prod=1.0
    for n in combo:
        prod*=weights[int(n)-1]
    return prod/z


def _at_least_one(p,m):
    return -math.expm1(float(m)*math.log1p(-float(p)))


def historical_equalization_backtest(game,draws,crowd):
    n_numbers=42 if game=="6/42" else 49
    c=math.comb(n_numbers,6)
    weights,m,target=calibrate_fixed_number_preferences(crowd,6)
    p_uniform=1.0/c
    pjack_uniform=_at_least_one(p_uniform,m)

    rows=[]
    for i,d in enumerate(draws):
        p=_combination_probability(d,weights,6)
        rows.append({
            "draw_index_newest_first":i,
            "actual":tuple(sorted(map(int,d))),
            "crowd_combo_probability":p,
            "uniform_combo_probability":p_uniform,
            "crowd_vs_uniform_combo_ratio":p/p_uniform,
            "crowd_jackpot_probability":_at_least_one(p,m),
            "equalized_jackpot_probability":pjack_uniform,
        })
    bt=pd.DataFrame(rows)

    return bt,{
        "game":game,
        "numbers":n_numbers,
        "ticket_count_assumed":m,
        "draws":len(bt),
        "uniform_combo_probability":p_uniform,
        "uniform_jackpot_probability":pjack_uniform,
        "historical_crowd_avg_jackpot_probability":float(bt.crowd_jackpot_probability.mean()),
        "historical_equalized_avg_jackpot_probability":float(bt.equalized_jackpot_probability.mean()),
        "historical_relative_change":float(pjack_uniform/bt.crowd_jackpot_probability.mean()-1),
        "historical_expected_jackpot_draws_crowd":float(bt.crowd_jackpot_probability.sum()),
        "historical_expected_jackpot_draws_equalized":float(bt.equalized_jackpot_probability.sum()),
    }


def theoretical_equalization(game,crowd,max_order=30):
    n_numbers=42 if game=="6/42" else 49
    c=math.comb(n_numbers,6)
    weights,m,target=calibrate_fixed_number_preferences(crowd,6)
    z=_esym(weights,6)[6]

    hit=0.0
    one=0.0
    bin_m=1.0
    bin_m1=1.0

    for r in range(1,max_order+1):
        bin_m*=((m-r+1)/r)
        wr=np.power(weights,r)
        moment=_esym(wr,6)[6]/(c*(z**r))
        hit+=((1.0 if r%2 else -1.0)*bin_m*moment)

        if r==1:
            bin_m1=1.0
        else:
            bin_m1*=((m-(r-1))/(r-1))
        one+=m*((1.0 if r%2 else -1.0)*bin_m1*moment)

        if r>10 and abs(bin_m*moment)<1e-16:
            break

    p=1.0/c
    equal_hit=_at_least_one(p,m)
    equal_one=m*p*((1-p)**(m-1))
    expected_winners=m/c

    return {
        "ticket_count_assumed":m,
        "expected_jackpot_winning_tickets":expected_winners,
        "crowd_probability_at_least_one":hit,
        "equalized_probability_at_least_one":equal_hit,
        "relative_change_at_least_one":equal_hit/hit-1,
        "crowd_probability_exactly_one":one,
        "equalized_probability_exactly_one":equal_one,
        "crowd_probability_multiple":hit-one,
        "equalized_probability_multiple":equal_hit-equal_one,
    }


def historical_lower_tier_equalization(game,draws,crowd,tiers=(3,4,5)):
    n_numbers=42 if game=="6/42" else 49
    total_combos=math.comb(n_numbers,6)
    weights,m,_=calibrate_fixed_number_preferences(crowd,6)
    z=_esym(weights,6)[6]

    def tier_prob(actual,h):
        aset=set(map(int,actual))
        win=[weights[n-1] for n in range(1,n_numbers+1) if n in aset]
        out=[weights[n-1] for n in range(1,n_numbers+1) if n not in aset]
        return _esym(win,h)[h]*_esym(out,6-h)[6-h]/z

    rows=[]
    summary=[]
    for h in tiers:
        uniform_p=(
            math.comb(6,h)*
            math.comb(n_numbers-6,6-h)/
            total_combos
        )
        equalized_count=m*uniform_p
        vals=[]
        for i,d in enumerate(draws):
            crowd_count=m*tier_prob(d,h)
            vals.append(crowd_count)
            rows.append({
                "draw_index_newest_first":i,
                "tier":h,
                "actual":tuple(sorted(map(int,d))),
                "crowd_expected_winners":crowd_count,
                "equalized_expected_winners":equalized_count,
                "crowd_vs_equalized_ratio":crowd_count/equalized_count,
            })

        arr=np.asarray(vals,dtype=float)
        crowd_mean=float(arr.mean())
        summary.append({
            "tier":h,
            "ticket_count_assumed":m,
            "uniform_ticket_probability":uniform_p,
            "equalized_expected_winners_per_draw":equalized_count,
            "historical_crowd_expected_winners_per_draw":crowd_mean,
            "equalization_change_winner_count":equalized_count/crowd_mean-1,
            "implied_equalization_change_payout_per_winner":crowd_mean/equalized_count-1,
            "crowd_sd":float(arr.std()),
            "crowd_cv":float(arr.std()/crowd_mean),
            "crowd_p10":float(np.quantile(arr,0.10)),
            "crowd_median":float(np.quantile(arr,0.50)),
            "crowd_p90":float(np.quantile(arr,0.90)),
            "crowd_min":float(arr.min()),
            "crowd_max":float(arr.max()),
        })

    return pd.DataFrame(rows),pd.DataFrame(summary)
