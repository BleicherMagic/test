# utils/rtl.py
import streamlit as st

def inject_rtl_css():
    st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"], .block-container { direction: rtl; text-align: right; }
    [data-testid="stTable"] table, [data-testid="stDataFrame"] table { direction: rtl; }
    [data-testid="stTable"] th, [data-testid="stTable"] td,
    [data-testid="stDataFrame"] th, [data-testid="stDataFrame"] td { text-align: right !important; unicode-bidi: plaintext; }
    [data-baseweb="select"] { direction: rtl; }
    input, textarea { direction: rtl; text-align: right; unicode-bidi: plaintext; }
    .stNumberInput input[type="number"] { direction: ltr !important; text-align: left !important; }
    code, pre, kbd, samp, a { direction: ltr; text-align: left; unicode-bidi: embed; }
    .ltr { direction: ltr !important; text-align: left !important; unicode-bidi: embed !important; }
    </style>
    """, unsafe_allow_html=True)
