import streamlit as st

# ✅ Kullanıcı giriş kontrolü
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("🔒 You must be logged in to access this page.")
    st.stop()
  
st.set_page_config(page_title="CREDIT Meeting Notes", page_icon="📝", layout="wide")
st.title("📝 CREDIT Meeting Notes")

st.write("Bu sayfada CREDIT toplantı notları yer alacak.")
