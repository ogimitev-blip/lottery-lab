from __future__ import annotations

import itertools
import json
import math
from collections import Counter

from lottery.data import load_custom_wheel

PREFIXES=(18,30,50,80,130)
POOL_SIZE=28
H_VALUES=(3,4,5,6)


def mask(line):
    m=0
    for x in line:
        m |= 1 << (int(x)-1)
    return m


def structural_stats(lines):
    out={}
    for n in PREFIXES:
        pref=lines[:n]
        exp=Counter(x for t in pref for x in t)
        overlaps=Counter()
        for i in range(len(pref)):
            a=set(pref[i])
            for j in range(i):
                overlaps[len(a & set(pref[j]))]+=1
        coverage={}
        for r in (2,3,4,5,6):
            seen=set()
            for t in pref:
                seen.update(itertools.combinations(sorted(t),r))
            coverage[str(r)]={
                "covered":len(seen),
                "universe":math.comb(POOL_SIZE,r),
                "pct":100.0*len(seen)/math.comb(POOL_SIZE,r),
            }
        out[str(n)]={
            "lines":n,
            "unique_lines":len(set(pref)),
            "exposure_min":min(exp.values()),
            "exposure_max":max(exp.values()),
            "exposure_mean":sum(exp.values())/POOL_SIZE,
            "pairwise_intersection_hist":{str(k):int(v) for k,v in sorted(overlaps.items())},
            "coverage":coverage,
        }
    return out


def exhaustive_capture(lines):
    masks=[mask(t) for t in lines]
    result={}
    for h in H_VALUES:
        hist={str(n):Counter() for n in PREFIXES}
        total=0
        for combo in itertools.combinations(range(1,POOL_SIZE+1),h):
            total+=1
            cm=mask(combo)
            best=0
            pi=0
            for idx,tm in enumerate(masks,1):
                v=(cm & tm).bit_count()
                if v>best:
                    best=v
                while pi<len(PREFIXES) and idx==PREFIXES[pi]:
                    hist[str(PREFIXES[pi])][best]+=1
                    pi+=1
            if pi != len(PREFIXES):
                raise RuntimeError("prefix traversal incomplete")
        per={}
        for n in PREFIXES:
            c=hist[str(n)]
            mean=sum(k*v for k,v in c.items())/total
            metrics={
                "universe":total,
                "best_hit_hist":{str(k):int(c.get(k,0)) for k in range(h+1)},
                "mean_best_hits":mean,
                "p_full_capture":c.get(h,0)/total,
            }
            for r in range(3,h+1):
                metrics[f"p_best_ge_{r}"]=sum(v for k,v in c.items() if k>=r)/total
            per[str(n)]=metrics
        result[str(h)]=per
    return result


def validate(lines):
    if len(lines)<max(PREFIXES):
        raise RuntimeError(f"Need at least {max(PREFIXES)} K28 lines")
    for i,t in enumerate(lines[:max(PREFIXES)],1):
        if len(t)!=6 or len(set(t))!=6:
            raise RuntimeError(f"Invalid line {i}: {t}")
        if min(t)<1 or max(t)>POOL_SIZE:
            raise RuntimeError(f"Out-of-range line {i}: {t}")
    if len(set(lines[:max(PREFIXES)]))!=max(PREFIXES):
        raise RuntimeError("K28 nested wheel has duplicate lines")


def main():
    lines=[tuple(map(int,t)) for t in load_custom_wheel()]
    validate(lines)
    structural=structural_stats(lines)
    capture=exhaustive_capture(lines)

    # Analytical null: n independent uniformly random 6-of-28 lines.
    # This is not a wheel guarantee, but a useful structural benchmark.
    single={}
    for r in (3,4,5,6):
        single[r]=sum(
            math.comb(6,k)*math.comb(22,6-k)
            for k in range(r,7)
        )/math.comb(28,6)
    random_benchmark={}
    for n in PREFIXES:
        random_benchmark[str(n)]={
            f"p{r}plus":1.0-(1.0-single[r])**n for r in (3,4,5,6)
        }

    headline={}
    for n in PREFIXES:
        h6=capture["6"][str(n)]
        h5=capture["5"][str(n)]
        h4=capture["4"][str(n)]
        headline[str(n)]={
            "given_pool_hits_6":{
                "p3plus":h6["p_best_ge_3"],
                "p4plus":h6["p_best_ge_4"],
                "p5plus":h6["p_best_ge_5"],
                "p6":h6["p_best_ge_6"],
                "mean_best":h6["mean_best_hits"],
            },
            "given_pool_hits_5":{
                "p3plus":h5["p_best_ge_3"],
                "p4plus":h5["p_best_ge_4"],
                "p5":h5["p_best_ge_5"],
                "mean_best":h5["mean_best_hits"],
            },
            "given_pool_hits_4":{
                "p3plus":h4["p_best_ge_3"],
                "p4":h4["p_best_ge_4"],
                "mean_best":h4["mean_best_hits"],
            },
            "random_line_benchmark_given_pool_hits_6":random_benchmark[str(n)],
            "delta_vs_random_pp_given_pool_hits_6":{
                "p3plus":100.0*(h6["p_best_ge_3"]-random_benchmark[str(n)]["p3plus"]),
                "p4plus":100.0*(h6["p_best_ge_4"]-random_benchmark[str(n)]["p4plus"]),
                "p5plus":100.0*(h6["p_best_ge_5"]-random_benchmark[str(n)]["p5plus"]),
                "p6":100.0*(h6["p_best_ge_6"]-random_benchmark[str(n)]["p6plus"]),
            },
        }

    print("K28_EXHAUSTIVE_BEGIN")
    print(json.dumps({
        "wheel":"systems/k28_nested_130.csv",
        "pool_size":POOL_SIZE,
        "prefixes":list(PREFIXES),
        "exhaustive_universes":{str(h):math.comb(POOL_SIZE,h) for h in H_VALUES},
        "structural":structural,
        "capture":capture,
        "independent_random_benchmark":random_benchmark,
        "headline":headline,
        "note":"Outcome-blind exhaustive structural test. For each possible set of h winning numbers inside K28 (h=3..6), computes the best overlap achieved by each nested wheel prefix."
    },indent=2))
    print("K28_EXHAUSTIVE_END")


if __name__=="__main__":
    main()
