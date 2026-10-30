# Lottery Lab — prospective four-line shape-hybrid research protocol
Date fixed: 2026-10-30 (after draw 85, before draw 86).
Status: RESEARCH_ONLY; no ticket purchases authorized.
Outcome cutoff for retrospective development: draw 85, 2026-10-29.

## Immutable experimental arms
For each future draw, freeze four ticket allocations per game BEFORE the draw:
- standard: current 4x6 balanced assignment
- one_shape: same 24 selected numbers, consolidate one consecutive/step-2 triple into one row with minimum swaps
- two_shape: start from one_shape, consolidate a same-final-digit triple into a different row; fall back to an adjacent pair if needed
- random_assignment: deterministic unbiased shuffle of the same 24 selected numbers, seed defined by (YYYYMMDD + 1000 * game_max_number + draw_number)

Each arm must contain 4 lines x 6 valid numbers, 24 distinct numbers, identical selected set, identical cost. Never treat shadow lines as purchased lines.

## Selection
6/49: K22 score and flexible pool using ONLY past draws, then two highest-scoring fresh numbers to reach 24.
6/42: K28 score and flexible pool using ONLY past draws, then first 24 numbers.
No target or later draws may enter any model calculation.

## Metrics
Primary: count of draws with any line matching >=3 numbers. Secondary: >=4, >=5, actual payouts and stake per proposed arm, mean best line.
Report pool coverage separately from line assignment and conditional expected P(3+) given pool hits.
Use rolling last 10/50 for diagnostics only; no refitting based on interim outcomes. Review after 30 and 50 future draws, compare with fair-draw combinatorial null and random control; correct for multiple tests.

## Guardrails
No increased budget (user currently prefers four lines in 6/49 and four in 6/42, <=EUR 10 per draw).
If fair uniform lottery draws, any fixed 4 mutually-disjoint lines have identical theoretical win probabilities regardless of shape.
Do not claim predictive edge absent new independent prospective evidence.
Do not change canonical production ticket allocation or overwrite draw 85 frozen tickets.
