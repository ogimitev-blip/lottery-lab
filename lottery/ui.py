import streamlit as st
def setup_page(title,icon='🎯'):
    st.set_page_config(page_title=title,page_icon=icon,layout='wide')
    st.markdown("<style>.block-container{padding-top:1.5rem;padding-bottom:3rem;max-width:1500px}.hero{padding:1.15rem 1.3rem;border:1px solid rgba(103,232,249,.18);border-radius:18px;background:linear-gradient(120deg,rgba(14,30,52,.96),rgba(8,17,31,.96));margin-bottom:1.1rem}.hero h1{margin:0;font-size:2rem}.hero p{margin:.4rem 0 0;color:#A7B5C9}[data-testid='stMetric']{background:#0E1A2B;border:1px solid rgba(255,255,255,.08);padding:12px;border-radius:14px}</style>",unsafe_allow_html=True)
def hero(title,subtitle):st.markdown(f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>',unsafe_allow_html=True)
def caveat():st.caption('Historical patterns are descriptive, not evidence that future lottery draws are predictable. Keep spending fixed and pre-committed.')
