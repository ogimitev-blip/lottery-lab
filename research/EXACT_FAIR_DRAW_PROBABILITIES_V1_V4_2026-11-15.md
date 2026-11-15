# Lottery Lab — Exact equal-probability audit of draw #90 proposed ticket structures

Research date: 2026-11-15. **This is an exhaustive theoretical fair-lottery calculation, not a predictive backtest.**

## Question
What changes in the probability of at least one exact-hit prize when the same lottery budget is allocated to (a) three pairs of similar 6/49 rows, versus (b) six fully disjoint rows?

## Method
Enumerated all **C(49,6) = 13,983,816** possible distinct six-number outcomes, uniformly weighted, and calculated the maximum exact number of matches in any proposed row for each outcome. The probability of at least one row with >=3, >=4, >=5, or exactly 6 matches is the number of outcomes meeting that threshold divided by 13,983,816.

Ticket sources:
- V1: `data/proposed_tickets_2026-11-15_draw90_paired_6x649.json`; six tickets, each variant retains four of six base numbers.
- V2: `data/proposed_tickets_2026-11-15_draw90_paired_6x649_v2_three_swaps.json`; six tickets, each variant retains three of six.
- V3: `data/proposed_tickets_2026-11-15_draw90_paired_6x649_v3_shape_mix.json`; six tickets, structural parity/step2/same-ending motifs, each variant retains three of six.
- V4: `data/proposed_tickets_2026-11-15_draw90_7x649_v4_added_shape.json`; V3 + one extra distinct seventh row.
- Disjoint six-row baseline from V1 `frozen_shadow_control.six_disjoint_lines`.

## Exhaustive results

| Proposal | Lines | Unique number coverage | P(any >=3 exact) | P(any >=4 exact) | P(any >=5 exact) | P(jackpot) |
|---|---:|---:|---:|---:|---:|---:|
| V1, 2 replacements | 6 | 24 | 9.468832% | 0.556500% | 0.011027% | 0.00004291% |
| V2, 3 replacements | 6 | 27 | 10.301544% | 0.583596% | 0.011113% | 0.00004291% |
| V3, 3 replacements + Shape | 6 | 27 | 10.301544% | 0.583596% | 0.011113% | 0.00004291% |
| V4, 7 tickets | 7 | 33 | 12.148565% | 0.682310% | 0.012965% | 0.00005006% |
| Six disjoint lines | 6 | 36 | 11.139620% | 0.592285% | 0.011113% | 0.00004291% |

The 7-row V4 costs more (€6.30 vs €5.40 at regular 2026 line price €0.90) and is **not an equal-budget comparison** with the six-line arms.

The six-line disjoint baseline offers about **+1.671 percentage points** absolute higher probability of at least one triple vs V1, and **+0.838 points** vs V2/V3 under the uniform model. All six distinct-line options have the same jackpot probability `6/13,983,816`. V2 and V3 theoretical coverage probabilities are identical: numerical magnitudes, parity, and cosmetic motifs have no ability to change fair-draw probabilities when pairwise and higher-order overlap structure is isomorphic.

## Observed draw #90 (user reported, pending independent official verification)

Numbers: 10, 11, 17, 30, 36, 37.

- V1's fourth line would have had **four** matches; V1 was superseded before the draw and is NOT a realized payout.
- V2: zero tickets with >=3 matches.
- V3 and V4: one ticket with three matches.
- Six-disjoint research baseline: zero tickets with >=3 matches.
- These realized outcomes are one draw only; they should not overturn the exact ex-ante probability comparison or be used to refit rules post hoc.

## Recommendation for future trials

1. Freeze alternatives **before** each draw: 3+3 paired (2-change), 3+3 paired (3-change), Shape, and an equal-cost disjoint-control set.
2. Track draw-level frequency of >=3 and >=4, stake, prize, and number of distinct values. Keep *numerical proximity* as a separate descriptive metric only.
3. Explore restricted wheels derived from BST System #9 as a **new control research arm**; the full 18-number / 48-combination guarantees DO NOT transfer to six or eight extracted lines. Do not claim otherwise.
4. Use prospective evaluation (30 and 50 draws) and blind walk-forward historical diagnostics with strict cutoff dates; avoid tuning to draw #90.

Reproducibility: Iterate six nested strictly increasing loops 0<=a<b<c<d<e<f<49, construct a 49-bit winning set, test `popcount(ticket_bitmask & winning_bitmask)`, compute `max` across rows and threshold tallies. No probabilistic simulation or external predictors were used.

**Bottom line:** There is no established predictive advantage in the near-miss or Shape patterns. Any differences above are exact combinatorial probabilities of a fair draw, not model forecasts.
