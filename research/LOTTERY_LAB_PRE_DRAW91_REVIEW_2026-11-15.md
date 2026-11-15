# Lottery Lab — Before Draw #91: retrospective audit (15 November 2026)

Status: research, **not independent validation**. Do not include BST's System #9 in the research protocol; the user asked about it solely for information.

## Data and limitations
- Repo input: `data/draws_649.csv`, 296 rows through confirmed draw #89 on 12 November 2026.
- Strict forward-only training for each *historical* predicted draw: last 100 to 295 **earlier rows** in that repository's reverse-chronological order. 196 targets tested. No target or later rows enter model score computation.
- Important source issue: **269 earlier CSV rows lack draw number and date**, so archive chronological integrity is **assumed from row order, not independently verified**. This weakens conclusions. Fix metadata and provenance before treating results as robust.
- Main selection: JS reproduction of Python `lottery/models.py` `ensemble_score` + `overdue` + `flex_pool` K22; select 18 highest scored K22 numbers into 3 balanced six-number main lines.
- V1: variants each keep four mains and replace two with ±1..2 previously unused numbers, preferring better pre-draw score and balanced parity.
- V2: variants each keep three mains and replace three with ±1..3 previously unused numbers, preferring better pre-draw score and balanced parity.
- Disjoint control: identical three main lines + three disjoint lines comprising the highest remaining scored 18 numbers. All six rows have 36 distinct numbers.
- Random control: six disjoint lines from a seeded uniform shuffle of 49 numbers. All arms = six lines and the same hypothetical cost.
- V3's exact manually constructed Shape variants were not replayed historically (that would be data-dependent). Shape patterns are checked separately against fair-draw combinatorial expectations.

## Walk-forward results: 196 historical target draws

| 6-line strategy | Draws with >=1 triple | Draws with >=1 four-match | Average best exact hits |
|---|---:|---:|---:|
| V1, 2 nearby replacements | 25 (12.76%) | 3 | 1.719 |
| V2, 3 nearby replacements | 22 (11.22%) | 3 | 1.776 |
| Six disjoint score-ranked lines | 19 (9.69%) | 1 | 1.837 |
| Six disjoint random lines | 21 (10.71%) | 1 | 1.801 |

These are observed outcomes, NOT fair-draw theoretical win probabilities (under fair draws, six disjoint lines have a higher *ex ante* probability of >=1 triple than overlapped paired lines). Exact probabilities separately audited in `research/EXACT_FAIR_DRAW_PROBABILITIES_V1_V4_2026-11-15.md`.

### Paired differences and stability
- V1 versus disjoint control: 13 draws had a triple in both; 12 only in V1; 6 only in disjoint; 165 in neither. Two-sided exact discordance sign/McNemar test **p≈0.238**. Insufficient evidence that V1 is genuinely superior.
- V1 vs V2: 8 only V1, 5 only V2, 17 both, p≈0.581.
- Earlier half of 98 targets: V1 15, V2 11, disjoint 9, random 12 with >=3.
- Later half of 98 targets: V1 10, V2 11, disjoint 10, random 9.
- Latest 60 target draws: V1 5, V2 5, disjoint 4, random 7; **no** 4+ in any arm. Apparent early V1 advantage is not stable.
- Multiple variants/motifs tested and rules were researched on overlapping historical data: nominal p-values are descriptive, not validated inferential evidence.

### K22 pool selection versus fair-draw expectation
- K22 top 22 pool: 2.84694 winning numbers per historical draw on average versus **2.69388 expected** for any fixed 22-number subset chosen before a fair draw. Difference +0.15306; descriptive z≈1.86 across 196 under a conditional hypergeometric fair-draw null; not strong or independent evidence of prediction.
- Top 18 main pool: 2.31633 vs fair-draw 2.20408.
- This is a retrospective test, and the underlying model had earlier been chosen using many of these outcomes, thus treat evidence as preliminary.

## Shape frequency check

Across those 196 actual historical outcomes:
- At least one run of three consecutive numbers: **7/196 = 3.57%** vs exact fair-lottery expectation **4.7696%**.
- At least one arithmetic triple with step 2: **10/196 = 5.10%** vs exact fair-lottery expectation **4.5743%**.
- At least three numbers with equal last digit: **19/196 = 9.69%** vs exact fair-lottery expectation **9.2158%**.
- These are in line with expected chance variability. No validated predictive benefit for forcing motifs.

Exact expectations calculated combinatorially:
- No three consecutive among six selected from 49: count via dynamic programming of 49 binary positions with selected-count 0..6 and current run-length 0..2. Probability = 1 - excluded/C(49,6).
- No step2 triple: separate analogous run-restricted binary chains for 24 even and 25 odd numbers, then convolve six selections.
- No three same ending: coefficient of x^6 in product over final-digit buckets (nine of size five and the zero-ending bucket size four) allowing each bucket contribution at most two. Probability = 1 - excluded/C(49,6).
- Denominator C(49,6) = **13,983,816**.

## Draw #90 outcomes (not included in 196-target historical test)
- User reported numbers **10,11,17,30,36,37**, pending BST confirmation (official portal still showed #89 at the time of this report).
- Superseded V1 ticket #4 would have hit four exact; it was NOT the user's final proposed selection.
- Final V4 ticket #4 had three exact; no inference about superiority from one draw.
- Detailed pre-frozen variant scoring stored in `data/draw90_user_reported_pending_2026-11-15_and_variant_analysis.json`.

## Direction ahead of draw #91
1. Preserve the user's preference for three main K22 tickets plus three variants; do **not** assume the two-swap variation is better based on this retrospective result.
2. Freeze V1 2-swap, V2 3-swap, a structurally diverse variant, and six disjoint controls before draw; do not retroactively substitute winning tickets.
3. Use known prices to keep the actual proposed six-line experiment within the user's usual €10 ceiling; any shadow strategies are virtual only.
4. Prioritize fixing missing draw IDs, dates, source provenance and validating the original archive order. Next, run a fresh verified-history walk-forward and track genuinely prospective draws from #91 onward.
5. Do not use any System #9 wheel unless the user explicitly requests renewed research.
6. Avoid claims that near misses, unusual patterns, overdue numbers, K22 scoring or post hoc shape selection forecast independent random draws.

Full per-target research data: `research/LOTTERY_LAB_WALK_FORWARD_AUDIT_2026-11-15.json`.

**Conclusion:** Research continuation is justified, but the defensible result is uncertainty. A 2-change approach won in 25 of 196 historical targets vs 19 for disjoint, a difference not statistically convincing and not stable across halves. Theoretically, disjoint tickets give a higher chance of any triple under a fair draw; every distinct six-number ticket has identical jackpot odds.
