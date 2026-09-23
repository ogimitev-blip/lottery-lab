import pandas as pd
LINE_PRICE_642=.80

def map_positions(pool,position_lines):
    if len(pool)!=28: raise ValueError('Expected K28 pool')
    return [tuple(pool[p-1] for p in line) for line in position_lines]

def ticket_frame(tickets):
    return pd.DataFrame([dict(line=i+1,**{f'n{j+1}':n for j,n in enumerate(t)}) for i,t in enumerate(tickets)])

def cost_642(n_lines): return n_lines*LINE_PRICE_642
