import streamlit as st
from lottery.ui import setup_page,hero,caveat
from lottery.version import APP_VERSION,MODEL_642,MODEL_649,WHEEL_642,WHEEL_649

setup_page('Model Info · Lottery Lab','🧠')
hero('Model Info','Frozen production rules are separated from ticket conversion and from experimental shadow modes.')

st.markdown(f"""
### 6/42 production — {MODEL_642}
For numbers 1–42: 25% last-20 frequency + 30% last-50 + 30% last-100 + 15% all-history; z-standardize across 42 numbers. If a number's gap exceeds 20 draws, add `(gap - 20) / 10` with λ=1.

**K28 repeat rule:** start Top-26. From each of the two immediately previous draws, add the highest-scoring outsider when available, then fill from the normal ranking.

Conversion wheel: **{WHEEL_642}**. Custom prefixes are 6 / 18 / 30 / 50 / 80 / 130 lines. Official System 36 is shown as a benchmark, not as the production wheel.

### 6/49 production — {MODEL_649}
The 6/49 model uses the frozen ensemble architecture (frequency/persistence + motif component + multi-horizon smooth score), overdue λ=0.75 above gap 20, then the same two-draw flex rule.

**K22 is production. K26 is shadow.** The app keeps them visually distinct.

Conversion: **{WHEEL_649}**. The six-ticket base emphasizes broad exposure; larger 11 / 16 / 22 / 28 / 33-line modes extend it with a diversity-oriented low-overlap construction.

### Selection vs conversion
A selection pool answers: *are the winning numbers inside the selected K?*  
A wheel answers: *given that pool, how effectively do the purchased six-number tickets convert it into 3/4/5/6 hits?*

At fixed **L distinct six-number tickets**, rearranging the wheel cannot change raw jackpot probability: it remains **L / C(N,6)**. Wheel design mainly changes lower-tier coverage and where coverage is concentrated.

### Crowd / sharing-risk layer
BST player-choice counts are kept outside the draw-selection model. Lottery Lab uses them only as a prize-sharing proxy. The experimental anti-crowd conversion keeps the selected pool and wheel incidence structure but can relabel number exposure toward less-played selected numbers. This does not change raw draw probabilities.

### Historical-depth research
The production models remain frozen on the existing history. A separate History Depth Lab appends a 2020–2023 research archive and evaluates the deeper-history variant leakage-free before any possible promotion.

### Data and prospective testing
Official BST draw syncing, draw numbers, dates and payout metadata are handled separately from the models. Prospective plays can be frozen before the draw so later scoring cannot benefit from hindsight.

**App version:** {APP_VERSION}
""")
caveat()
