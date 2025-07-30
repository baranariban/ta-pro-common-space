import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Production Tracker", layout="wide")
st.title("🏭 Production Tracker")

# 🔐 Giriş kontrolü
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("🔒 You must be logged in to access this page.")
    st.stop()

current_user = st.session_state.get("username", "unknown")

# 📁 Kalıcı kayıt dosyası
DATA_FILE = "production_records.csv"
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
else:
    df = pd.DataFrame(columns=[
        "Production Name", "Raw Material", "Producer",
        "Process Parameters", "Production Date",
        "Tests Planned/Done", "Sample Count",
        "Recorded By", "Entry Date"
    ])

# 📋 Giriş Formu
st.subheader("➕ Create New Production Entry")

with st.form("entry_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        prod_name = st.text_input("Production Name", placeholder="e.g. Sample Batch #45")
        raw_material = st.text_input("Raw Material", placeholder="e.g. Polyamide 66")
        producer = st.text_input("Producer", placeholder="e.g. Zeynep Ege Uysal")
        sample_count = st.number_input("Sample Count", min_value=1, step=1)

    with col2:
        prod_date = st.date_input("Production Date")
        tests = st.text_area("Tests Planned/Done", placeholder="e.g. Tensile, DMA, TGA")
        process_params = st.text_area("Process Parameters", placeholder="e.g. Temp=250°C, Speed=120 RPM")

    submitted = st.form_submit_button("Save Entry")

    if submitted:
        new_entry = pd.DataFrame([{
            "Production Name": prod_name,
            "Raw Material": raw_material,
            "Producer": producer,
            "Process Parameters": process_params,
            "Production Date": prod_date.strftime("%Y-%m-%d"),
            "Tests Planned/Done": tests,
            "Sample Count": int(sample_count),
            "Recorded By": current_user,
            "Entry Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])
        df = pd.concat([df, new_entry], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        st.success("✅ Entry saved successfully.")
        st.rerun()

# 📊 Kayıtlı Veriler
st.subheader("📋 All Production Records")
if df.empty:
    st.info("No entries yet.")
else:
    st.dataframe(df, use_container_width=True)
