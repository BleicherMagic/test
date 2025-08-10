import streamlit as st

def inject_dark_theme():
    with open("utils/theme_dark.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
