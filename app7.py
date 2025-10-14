import streamlit as st
from app4 import app as app1_main
from app5 import app as app2_main
from app6 import app as app3_main

st.set_page_config(page_title="Unified Streamlit App", layout="wide")

st.title("🏠 Combined Streamlit Application")

tab1, tab2, tab3 = st.tabs(["🔍 RESEDENTIAL", "📊 COMMERCIAL", "⚙️ PG"])

with tab1:
    app1_main()

with tab2:
    app2_main()

with tab3:
    app3_main()
