import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
BG='#08111F'

def clean(fig,height=None):
    fig.update_layout(template='plotly_dark',paper_bgcolor=BG,plot_bgcolor=BG,margin=dict(l=35,r=20,t=55,b=35),hoverlabel=dict(font_size=13))
    if height: fig.update_layout(height=height)
    return fig

def draw_map(draws,window,n_numbers,labels=None,backtest=None,show_model=True,show_repeat=False):
    shown=draws[:window]; z=np.zeros((len(shown),n_numbers),int); hover=np.empty((len(shown),n_numbers),object)
    btmap={int(r.draw_index_newest_first):r for _,r in backtest.iterrows()} if backtest is not None else {}
    y=[]
    for i,d in enumerate(shown):
        y.append((labels[i] if labels and i<len(labels) and labels[i] else ('Latest' if i==0 else f'{i} ago')))
        actual=set(map(int,d)); r=btmap.get(i); pool=set(r.pool) if r is not None else set(); reps=set(r.repeat_additions) if r is not None else set()
        for n in range(1,n_numbers+1):
            if n in actual: z[i,n-1]=(1 if (not show_model or r is None or n in pool) else 2)
            if show_repeat and n in reps and n not in actual: z[i,n-1]=3
            parts=[f'Number {n}',f"Draw: {' '.join(map(str,sorted(actual)))}"]
            if r is not None:
                parts.append(f'Pool capture: {int(r.pool_hits)}/6')
                if n in reps: parts.append('Repeat-rule addition')
                if n in actual and n not in pool: parts.append('Outside historical pool')
            hover[i,n-1]='<br>'.join(parts)
    cs=[[0,'#0B1627'],[.24,'#0B1627'],[.25,'#22C55E'],[.49,'#22C55E'],[.50,'#F97316'],[.74,'#F97316'],[.75,'#67E8F9'],[1,'#67E8F9']]
    fig=go.Figure(go.Heatmap(z=z,x=list(range(1,n_numbers+1)),y=y,zmin=0,zmax=3,colorscale=cs,showscale=False,text=hover,hovertemplate='%{text}<extra></extra>',xgap=1,ygap=1))
    fig.update_xaxes(dtick=1,side='top'); fig.update_yaxes(autorange='reversed',title='Draw')
    height=520 if window<=20 else (760 if window<=50 else (1100 if window<=100 else 1600))
    fig.update_layout(title='Draw map',height=height)
    return clean(fig)

def frequency_grid(draws,window,n_numbers):
    shown=draws[:min(window,len(draws))]; counts={n:sum(n in d for d in shown) for n in range(1,n_numbers+1)}
    cols=7; rows=math.ceil(n_numbers/cols); z=np.full((rows,cols),np.nan); text=np.empty((rows,cols),object); hover=np.empty((rows,cols),object)
    text[:]=''; hover[:]=''
    for n in range(1,n_numbers+1):
        r=(n-1)//cols;c=(n-1)%cols;z[r,c]=counts[n];text[r,c]=str(n);hover[r,c]=f'Number {n}<br>{counts[n]} appearances in last {len(shown)} draws'
    fig=go.Figure(go.Heatmap(z=z,text=text,texttemplate='%{text}',textfont={'size':16},customdata=hover,hovertemplate='%{customdata}<extra></extra>',colorscale='Viridis',xgap=4,ygap=4))
    fig.update_xaxes(showticklabels=False);fig.update_yaxes(showticklabels=False,autorange='reversed');fig.update_layout(title=f'Frequency grid — last {len(shown)} draws',height=500)
    return clean(fig)

def gap_chart(draws,n_numbers):
    gp={n:next((i for i,d in enumerate(draws) if n in d),len(draws))+1 for n in range(1,n_numbers+1)}
    df=pd.DataFrame({'number':list(gp),'gap':list(gp.values())}).sort_values('gap')
    fig=px.bar(df,x='gap',y=df.number.astype(str),orientation='h',labels={'x':'Current gap (draws)','y':'Number'})
    fig.add_vline(x=20,line_dash='dash',annotation_text='threshold 20');fig.update_layout(title='Current gaps',height=max(760,n_numbers*18))
    return clean(fig),df.sort_values('gap',ascending=False)

def rolling_frequency(draws,numbers,window):
    chron=list(reversed(draws));x=np.arange(1,len(chron)+1);fig=go.Figure()
    for n in numbers:
        a=pd.Series([int(n in d) for d in chron]);roll=a.rolling(window,min_periods=1).mean()*100;fig.add_trace(go.Scatter(x=x,y=roll,mode='lines',name=str(n)))
    fig.update_layout(title=f'Rolling {window}-draw appearance rate',height=460,xaxis_title='Chronological draw index',yaxis_title='Appearance rate (%)')
    return clean(fig)

def pair_matrix(draws,window,n_numbers):
    shown=draws[:min(window,len(draws))];m=np.zeros((n_numbers,n_numbers),int)
    for d in shown:
        vals=sorted(set(map(int,d)))
        for a in vals:
            for b in vals:
                if a!=b:m[a-1,b-1]+=1
    fig=go.Figure(go.Heatmap(z=m,x=list(range(1,n_numbers+1)),y=list(range(1,n_numbers+1)),colorscale='Viridis',hovertemplate='Pair %{x}–%{y}: %{z}<extra></extra>'))
    fig.update_layout(title=f'Pair co-occurrence — last {len(shown)} draws',height=760);fig.update_yaxes(autorange='reversed')
    return clean(fig)

def performance_timeline(bt):
    d=bt.sort_values('draw_index_newest_first',ascending=False).reset_index(drop=True);x=np.arange(1,len(d)+1);fig=go.Figure()
    fig.add_trace(go.Scatter(x=x,y=d.pool_hits,mode='lines+markers',name='Selection-pool hits'));fig.add_trace(go.Scatter(x=x,y=d.best_ticket_hits,mode='lines+markers',name='Best ticket hits'))
    for y in [4,5,6]:fig.add_hline(y=y,line_dash='dot',opacity=.35)
    fig.update_layout(title='Selection vs conversion through time',height=500,xaxis_title='OOS draw index (oldest → newest)',yaxis_title='Hits',yaxis=dict(range=[0,6.3],dtick=1))
    return clean(fig)
