# Lottery Lab: pre-draw #91 diagnostic review — 2026-11-15

Status: **exploratory retrospective / unverified archival chronology**, NOT a prospective performance claim.

## Scope and boundaries
- No use of Bulgarian Lotto's **System #9** in this review; user asked about that system solely for information, and expressly excluded it from the strategy.
- Reviewed `data/draws_649.csv` on 2026-11-15 (at start: 296 ordered rows, earliest 27 rows have draw number+date, 269 older records have blank draw number/date).
- Most recent official verified draw: #89, 2026-11-12, 7, 15, 18, 21, 30, 33.
- Draw #90, 2026-11-15, 10, 11, 17, 30, 36, 37, was reported by the user but was NOT yet on the official result page when checked; exclude #90 from this historical sample.
- The 150 most recent rows #89 backward are evaluated, each with **only strictly older draws** as training history, at least 146 older records at the oldest test point. Of 150 targets, **27 explicitly dated and 123 undated**. Order of undated archival records is presumed but not fully verified.

## Scoring rules
- K22 pool: historical `lottery/models.py` production score (smooth frequencies 20/50/100/full, FM/PS momentum & neighboring motifs, >20-gap overdue overlay), flexible `rank top 20 plus one from each of two prior draws where possible`.
- Pool22 evaluation: total winners inside the pre-draw 22-number pool (regardless of ticket placement).
- Pairing models: select highest scoring 18 from K22 pool, allocate into three six-number rows by ranked bands and even/high balancing. Variant rows are deterministically constructed by replacing 2, respectively 3, original values with available historical-score-ranked numeric neighbors at distance <=2 or <=3, excluding all main row numbers and avoiding duplicate replacement numbers between pairs.
- Disjoint six-line comparator: same three base rows plus three six-number rows from the next 18 highest-ranked numbers outside the bases; all 36 numbers unique.
- Four-line Shape control: select 24 from K22 plus top two additional outside values; split across four nonoverlapping rows by ranked assignment; Shape version consolidates an available three-consecutive or three-step-two motif through minimum swaps, preserving exactly the same 24 numbers, then compares against the unmodified four-row allocation.
- Per target: count any >=3 and any >=4 exact matches; note each six-line arm has the same stake, the four-line arms also have the same stake as each other. **The model-selection rules are researcher-specified and were developed after earlier visible historical outcomes. This is historical walk-forward scoring, not a blind prospective trial.**

## Walk-forward output: 150 provisional targets

| Strategy | Rows | >=3 exact draw-level events | >=4 | Mean best row hits |
|---|---:|---:|---:|---:|
| Paired 2 changes | 6 | 10 / 150 (6.67%) | 1 | 1.507 |
| Paired 3 changes | 6 | 10 / 150 (6.67%) | 1 | 1.480 |
| Six disjoint | 6 | 17 / 150 (11.33%) | 1 | 1.860 |
| Four rows with Shape | 4 | 11 / 150 (7.33%) | 0 | 1.647 |
| Four unmodified rows | 4 | 15 / 150 (10.00%) | 0 | 1.647 |

All 150 windows produced valid 6-line paired candidates at +/-2 and +/-3, and an available three-number sequence or step-two shape existed for all four-row test pools.

**Explicitly dated 27 recent draw targets only:**
- Paired 2 changes: 4 / 27 had >=3;
- Paired 3 changes: 1 / 27;
- Six disjoint: 1 / 27;
- Four-row Shape: 4 / 27;
- Four-row original: 4 / 27.

These small subgroups exhibit strong instability and do not prove a model advantage.

## Pool coverage
- K22: 439 / 150 = **2.927** winning values covered per draw on average.
- Fair uniform lottery reference for any preselected 22 distinct numbers: 6×22/49 = **2.694**.
- The chosen 18 K22 core numbers: **2.413** per draw, versus uniform 6×18/49 = **2.204**.
- The 36-number disjoint set: **4.513** per draw, versus uniform 6×36/49 = **4.408**.

**Caveats:** K22's historical above-baseline pool coverage is a *hypothesis-generating observation*, NOT proof of skill. The model was developed/tuned using historical data, the old data are not date-stamped, and many analytic choices have been tested. A fair-draw null must be assessed prospectively on independent data with corrected multiple-testing control. Recent-dated subset too short to support a predictive inference.

## Interpretation
1. The theoretical result calculated separately in `research/EXACT_FAIR_DRAW_PROBABILITIES_V1_V4_2026-11-15.md` favors six disjoint lines for the probability of any triple (11.14% vs 9.47% for four-overlap pair variants, 10.30% for three-overlap variants). Historical aggregate follows that direction, with unreliable small-sample variation.
2. Both paired versions and Shape versions remain legitimate research arms, but should not be called mathematically superior because of individual near-miss outcomes (such as draws #88/#90).
3. Fair draw distribution is invariant to a fixed ticket's parity, numeric proximity, ending digit, and sequence. What changes by allocation is overlap between tickets and payout correlations, not draw predictability.
4. For #91 keep same budget constraints; freeze all selected tickets **before** the next draw, with a paired arm and equal-cost six-disjoint research comparison. If the user's primary objective is maximize the probability of at least one prize-qualifying triple from six tickets under the fair null, the six-disjoint arm has the better ex-ante chance.
5. Before any stronger historical claims, reconstruct the missing date/draw-number metadata for 269 archive rows, validate chronology and provenance, and run independent holdout/prospective evaluation.
6. System #9 is **not** part of the research proposal or recommended ticket generation. Its earlier mention was informational only.

## Results do not demonstrate
- Forecastability of lotteries, improved number likelihood from gaps, nearest-neighbor numeric proximity, or Shape motifs.
- Financial ROI or profitability. Winning 3-number draws are not sufficient to establish economic value; costs and payout sizes must be accounted for.
- Official verification of #90's result or payout as of this research check.
