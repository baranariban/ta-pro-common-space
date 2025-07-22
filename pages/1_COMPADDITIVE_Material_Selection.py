import streamlit as st

# ✅ Kullanıcı giriş kontrolü
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("🔒 You must be logged in to access this page.")
    st.stop()
  
st.set_page_config(page_title="COMPADDITIVE Material Selection", page_icon="🧪", layout="wide")
st.title("🧪 COMPADDITIVE Material Selection")

st.write("Bu sayfada COMPADDITIVE malzeme seçimi yapılacak.")
