import streamlit as st
from lottery.ui import setup_page, hero, caveat

setup_page('Model Info · Lottery Lab', '🧠')
hero('Model Info', 'Simple, reproducible selection rules; conversion kept separate.')

st.markdown("""
### Selection score
For numbers 1–42: 25% last-20 frequency + 30% last-50 + 30% last-100 + 15% all-history; then z-standardize across 42 numbers.

### Overdue adjustment
For gaps above 20 draws add `(gap - 20) / 10` with λ=1.

### K28 repeat rule
Start Top-26. From each of the two immediately previous draws, add the highest-scoring outsider when available, then fill from normal ranking.

### Conversion
The custom wheel is nested: 18 → 30 → 50 → 80 → 130 lines. Earlier lines remain when the system grows. Wheel design mainly changes 3+/4+/5+ coverage; at fixed count of distinct lines it does not magically improve raw jackpot probability.

### Visuals
The draw map distinguishes historical model hits from model misses. Frequency, gaps and pair matrices describe history; they are not claims that future draws become more likely.
""")
caveat()
