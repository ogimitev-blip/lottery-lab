from __future__ import annotations

import itertools
import json
import math
import random
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from lottery.models import production_score_649, flex_pool

ROOT = Path(__file__).resolve().parents[1]
DRAW_PATH = ROOT / "data" / "draws_649.csv"

N_LINES = 555
MIN_HISTORY = 100
MAX_TARGETS = 150
PROPOSALS = 96

PORTFOLIOS = {
    "K22_ONLY_555": {"kind": "pure", "k": 22},
    "MIX_400_100_55": {"kind": "mix", "q": (400, 100, 55)},
    "MIX_300_170_85": {"kind": "mix", "q": (300, 170, 85)},
    "MIX_200_220_135": {"kind": "mix", "q": (200, 220, 135)},
    "K26_ONLY_555": {"kind": "pure", "k": 26},
}


def _schedule(q, seed):
    a, b, c = map(int, q)
    labels = ["6+0"] * a + ["5+1"] * b + ["4+2"] * c
    random.Random(seed).shuffle(labels)
    return labels


def _targets_for_mix(q):
    a, b, c = map(int, q)
    core_slots = 6 * a + 5 * b + 4 * c
    out_slots = b + 2 * c
    return (
        {n: core_slots / 22.0 for n in range(1, 23)}
        | {n: out_slots / 27.0 for n in range(23, 50)}
    )


def _sample_candidate(rng, label):
    core = list(range(1, 23))
    outside = list(range(23, 50))
    if label == "6+0":
        return tuple(sorted(rng.sample(core, 6)))
    if label == "5+1":
        return tuple(sorted(rng.sample(core, 5) + rng.sample(outside, 1)))
    if label == "4+2":
        return tuple(sorted(rng.sample(core, 4) + rng.sample(outside, 2)))
    raise ValueError(label)


def _sample_pure(rng, k):
    return tuple(sorted(rng.sample(list(range(1, k + 1)), 6)))


def _greedy_layout(name, spec, seed=20260925):
    rng = random.Random(seed + sum(ord(c) for c in name))
    selected = []
    selected_set = set()
    c4, c3, c2, exp = Counter(), Counter(), Counter(), Counter()

    if spec["kind"] == "mix":
        schedule = _schedule(spec["q"], seed + 17)
        targets = _targets_for_mix(spec["q"])
    else:
        k = int(spec["k"])
        schedule = ["pure"] * N_LINES
        targets = {n: 6 * N_LINES / k for n in range(1, k + 1)}

    for step, label in enumerate(schedule):
        frac = (step + 1) / N_LINES
        best = None
        best_key = None
        tries = 0
        proposals = set()
        while len(proposals) < PROPOSALS and tries < PROPOSALS * 20:
            tries += 1
            t = _sample_candidate(rng, label) if label != "pure" else _sample_pure(rng, spec["k"])
            if t not in selected_set:
                proposals.add(t)
        if not proposals:
            raise RuntimeError(f"No candidates for {name} at {step}")

        for t in proposals:
            q4 = list(itertools.combinations(t, 4))
            q3 = list(itertools.combinations(t, 3))
            q2 = list(itertools.combinations(t, 2))
            new4 = sum(c4[x] == 0 for x in q4)
            new3 = sum(c3[x] == 0 for x in q3)
            dup4 = sum(c4[x] for x in q4)
            dup3 = sum(c3[x] for x in q3)
            dup2 = sum(c2[x] for x in q2)

            exposure_delta = 0.0
            for n in t:
                target_now = targets[n] * frac
                before = (exp[n] - target_now) ** 2
                after = (exp[n] + 1 - target_now) ** 2
                exposure_delta += after - before

            # Coverage dominates; exposure balance resolves most late-stage ties.
            # Position/rank is deliberately not rewarded here: the selection model
            # already decides the K22 membership and the hedge should remain broad.
            key = (new4, new3, -dup4, -dup3, -dup2, -exposure_delta, -sum(t))
            if best_key is None or key > best_key:
                best_key = key
                best = t

        selected.append(best)
        selected_set.add(best)
        for x in itertools.combinations(best, 4):
            c4[x] += 1
        for x in itertools.combinations(best, 3):
            c3[x] += 1
        for x in itertools.combinations(best, 2):
            c2[x] += 1
        for n in best:
            exp[n] += 1

    if len(selected) != N_LINES or len(selected_set) != N_LINES:
        raise AssertionError(f"{name}: layout uniqueness failure")

    return selected


def _coverage(layout):
    c4 = Counter(x for t in layout for x in itertools.combinations(t, 4))
    c3 = Counter(x for t in layout for x in itertools.combinations(t, 3))
    c2 = Counter(x for t in layout for x in itertools.combinations(t, 2))
    exp = Counter(x for t in layout for x in t)
    vals = np.array(list(exp.values()), dtype=float)
    return {
        "lines": len(layout),
        "unique_4sets": len(c4),
        "duplicate_4set_incidence": int(sum(max(v - 1, 0) for v in c4.values())),
        "unique_3sets": len(c3),
        "duplicate_3set_incidence": int(sum(max(v - 1, 0) for v in c3.values())),
        "unique_pairs": len(c2),
        "exposure_min": int(vals.min()),
        "exposure_max": int(vals.max()),
        "exposure_cv": float(vals.std() / vals.mean()),
    }


def _map_mix(layout, pool22, score):
    pset = set(map(int, pool22))
    outside = sorted(
        [n for n in range(1, 50) if n not in pset],
        key=lambda n: (-float(score.loc[n]), int(n)),
    )
    ranked = list(map(int, pool22)) + list(map(int, outside))
    return [tuple(ranked[p - 1] for p in t) for t in layout]


def _map_pure(layout, pool):
    p = list(map(int, pool))
    return [tuple(p[pos - 1] for pos in t) for t in layout]


def _metrics(tickets, actual):
    aset = set(map(int, actual))
    hits = np.array([len(set(t) & aset) for t in tickets], dtype=int)
    return {
        "best_hits": int(hits.max()),
        "n3plus": int((hits >= 3).sum()),
        "n4plus": int((hits >= 4).sum()),
        "n5plus": int((hits >= 5).sum()),
        "n6": int((hits == 6).sum()),
    }


def _summary(df):
    if df.empty:
        return {}
    return {
        "draws": int(len(df)),
        "best_mean": float(df.best_hits.mean()),
        "p3plus": float((df.best_hits >= 3).mean()),
        "p4plus": float((df.best_hits >= 4).mean()),
        "p5plus": float((df.best_hits >= 5).mean()),
        "p6": float((df.best_hits == 6).mean()),
        "mean_3plus_lines": float(df.n3plus.mean()),
        "mean_4plus_lines": float(df.n4plus.mean()),
        "mean_5plus_lines": float(df.n5plus.mean()),
        "total_3plus_lines": int(df.n3plus.sum()),
        "total_4plus_lines": int(df.n4plus.sum()),
        "total_5plus_lines": int(df.n5plus.sum()),
        "total_6_lines": int(df.n6.sum()),
    }


def _conditional(df):
    out = {}
    for h, g in df.groupby("k22_hits"):
        out[str(int(h))] = {
            "draws": int(len(g)),
            "best_mean": float(g.best_hits.mean()),
            "p4plus": float((g.best_hits >= 4).mean()),
            "p5plus": float((g.best_hits >= 5).mean()),
            "mean_4plus_lines": float(g.n4plus.mean()),
            "mean_5plus_lines": float(g.n5plus.mean()),
        }
    return out


def _theory():
    den = math.comb(49, 6)
    probs = {}
    for h in range(7):
        probs[str(h)] = math.comb(6, h) * math.comb(43, 6 - h) / den
    return {
        "jackpot_probability_555_unique": N_LINES / den,
        "jackpot_odds_1_in": den / N_LINES,
        "expected_lines_by_hits": {h: N_LINES * p for h, p in probs.items()},
    }


def main():
    raw = pd.read_csv(DRAW_PATH)
    cols = [f"n{i}" for i in range(1, 7)]
    draws = [list(map(int, row)) for row in raw[cols].to_numpy().tolist()]
    limit = min(MAX_TARGETS, len(draws) - MIN_HISTORY)
    if limit < 50:
        raise RuntimeError("Insufficient history")

    layouts = {name: _greedy_layout(name, spec) for name, spec in PORTFOLIOS.items()}
    coverage = {name: _coverage(layout) for name, layout in layouts.items()}

    rows = []
    for i in range(limit):
        actual = draws[i]
        hist = draws[i + 1 :]
        score, _ = production_score_649(hist)
        pool22, _ = flex_pool(score, hist, 22)
        pool26, _ = flex_pool(score, hist, 26)
        k22_hits = len(set(pool22) & set(actual))
        k26_hits = len(set(pool26) & set(actual))

        for name, spec in PORTFOLIOS.items():
            if spec["kind"] == "mix":
                tickets = _map_mix(layouts[name], pool22, score)
            elif spec["k"] == 22:
                tickets = _map_pure(layouts[name], pool22)
            else:
                tickets = _map_pure(layouts[name], pool26)
            tm = _metrics(tickets, actual)
            rows.append({
                "target_index_newest_first": i,
                "portfolio": name,
                "k22_hits": k22_hits,
                "k26_hits": k26_hits,
                **tm,
            })

    bt = pd.DataFrame(rows)
    windows = {
        "LATEST_50": (0, 50),
        "PRIOR_100": (50, min(150, limit)),
        "FULL_150": (0, min(150, limit)),
    }

    summaries = {}
    conditionals = {}
    for w, (lo, hi) in windows.items():
        if hi <= lo:
            continue
        summaries[w] = {}
        conditionals[w] = {}
        for name in PORTFOLIOS:
            x = bt[(bt.portfolio == name) & (bt.target_index_newest_first >= lo) & (bt.target_index_newest_first < hi)]
            summaries[w][name] = _summary(x)
            conditionals[w][name] = _conditional(x)

    pool_rows = bt.drop_duplicates("target_index_newest_first")[["target_index_newest_first", "k22_hits", "k26_hits"]]
    pool_summary = {}
    for w, (lo, hi) in windows.items():
        x = pool_rows[(pool_rows.target_index_newest_first >= lo) & (pool_rows.target_index_newest_first < hi)]
        if x.empty:
            continue
        pool_summary[w] = {
            "draws": int(len(x)),
            "k22_mean_hits": float(x.k22_hits.mean()),
            "k22_p4plus": float((x.k22_hits >= 4).mean()),
            "k22_p5plus": float((x.k22_hits >= 5).mean()),
            "k22_p6": float((x.k22_hits == 6).mean()),
            "k26_mean_hits": float(x.k26_hits.mean()),
            "k26_p4plus": float((x.k26_hits >= 4).mean()),
            "k26_p5plus": float((x.k26_hits >= 5).mean()),
            "k26_p6": float((x.k26_hits == 6).mean()),
        }

    result = {
        "design": {
            "lines": N_LINES,
            "ordinary_cost_eur": 0.90 * N_LINES,
            "min_history": MIN_HISTORY,
            "targets": limit,
            "portfolio_specs": PORTFOLIOS,
            "note": "Strict walk-forward with respect to each target draw. Conversion layouts are frozen position layouts generated without outcomes. This is not an untouched model-development holdout because the production selection model was developed using historical research.",
        },
        "theory": _theory(),
        "coverage": coverage,
        "pool_selection": pool_summary,
        "summary": summaries,
        "conditional_on_k22_hits": conditionals,
    }

    print("BACKTEST_649_500_JSON_BEGIN")
    print(json.dumps(result, indent=2, sort_keys=True))
    print("BACKTEST_649_500_JSON_END")


if __name__ == "__main__":
    main()
