import streamlit as st
import pandas as pd
import os
import io
import datetime
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import savgol_filter, find_peaks

st.set_page_config(page_title="DSC Library", page_icon="🔬", layout="wide")
st.title("🔬 DSC Library")

current_user = st.session_state.get("username", "unknown")

# 📁 Kalıcı kayıt dosyaları
UPLOAD_DIR = "dsc_uploads"
META_FILE = "dsc_uploads_metadata.csv"
os.makedirs(UPLOAD_DIR, exist_ok=True)

if os.path.exists(META_FILE):
    meta_df = pd.read_csv(META_FILE)
else:
    meta_df = pd.DataFrame(columns=["file_name", "custom_name", "uploaded_by", "upload_time"])

# =============================
# 1) DOSYA YÜKLEME
# =============================
st.subheader("📤 Upload DSC Raw Data")
uploaded_file = st.file_uploader("Upload your DSC .txt file", type=["txt"])
custom_name = st.text_input("Custom name for this file")

if uploaded_file is not None and st.button("Save Upload"):
    save_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    new_entry = {
        "file_name": uploaded_file.name,
        "custom_name": custom_name if custom_name else uploaded_file.name,
        "uploaded_by": current_user,
        "upload_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
   
    if current_user == "unknown":
        st.warning("Logged-in username not found in session. Please ensure login sets st.session_state['username'].")

    meta_df = pd.concat([meta_df, pd.DataFrame([new_entry])], ignore_index=True)
    meta_df.to_csv(META_FILE, index=False)
    st.success(f"File {uploaded_file.name} uploaded successfully!")

# =============================
# 2) YÜKLENEN DOSYALAR TABLOSU
# =============================
st.subheader("📂 Uploaded DSC Files")
st.dataframe(meta_df, use_container_width=True)

# --- Row-wise delete UI ---
if not meta_df.empty:
    st.caption("Click Delete to remove a file and its record.")
    header_cols = st.columns([4,4,2,3,1])
    header_cols[0].markdown("**file_name**")
    header_cols[1].markdown("**custom_name**")
    header_cols[2].markdown("**uploaded_by**")
    header_cols[3].markdown("**upload_time**")
    header_cols[4].markdown("**Delete**")

    # We iterate over a copy with reset_index to safely map rows
    for _, row in meta_df.reset_index().iterrows():
        cols = st.columns([4,4,2,3,1])
        cols[0].write(row["file_name"])
        cols[1].write(row["custom_name"])
        cols[2].write(row["uploaded_by"])
        cols[3].write(row["upload_time"])

        # unique key per row
        if cols[4].button("Delete", key=f"del_{row['file_name']}"):
            # 1) Delete the physical file if exists
            try:
                file_to_delete = os.path.join(UPLOAD_DIR, row["file_name"])
                if os.path.exists(file_to_delete):
                    os.remove(file_to_delete)
            except Exception as e:
                st.error(f"File delete error: {e}")

            # 2) Remove from metadata (match by file_name & custom_name for safety)
            try:
                mask = (meta_df["file_name"] == row["file_name"]) & (meta_df["custom_name"] == row["custom_name"])
                meta_df = meta_df.loc[~mask].reset_index(drop=True)
                meta_df.to_csv(META_FILE, index=False)
                st.success(f"Deleted: {row['file_name']}")
            except Exception as e:
                st.error(f"Metadata update error: {e}")

            st.rerun()
# =============================
# 3) DOSYA SEÇİMİ
# =============================
if not meta_df.empty:
    selected_file = st.selectbox("Select a file to analyze", meta_df["custom_name"])
    file_row = meta_df[meta_df["custom_name"] == selected_file].iloc[0]
    file_path = os.path.join(UPLOAD_DIR, file_row["file_name"])

    if os.path.exists(file_path):
        # -----------------
        # RAW DATA OKUMA
        # -----------------
        with open(file_path, "r", encoding="latin1") as f:
            lines = f.readlines()

        data = []
        for line in lines[56:]:
            parts = line.strip().split()
            if len(parts) == 3:
                try:
                    data.append([float(parts[0]), float(parts[1]), float(parts[2])])
                except:
                    pass

        dsc_df = pd.DataFrame(data, columns=["Time_min", "Temperature_C", "HeatFlow_mW"])

        st.subheader("📋 Raw Data")
        st.dataframe(dsc_df.head(100))  # ilk 100 satır gösterelim

        # -----------------
        # GRAFİK
        # -----------------
        st.subheader("📊 DSC Curve")
        fig, ax = plt.subplots(figsize=(8,5))
        ax.plot(dsc_df["Temperature_C"], dsc_df["HeatFlow_mW"], label=selected_file)
        ax.set_xlabel("Temperature (°C)")
        ax.set_ylabel("Heat Flow (mW)")
        ax.legend()
        ax.grid(True)
        st.pyplot(fig)

        # -----------------
        # ANALİZ (Tg, Tc, Tm, ΔH, Kristallik)
        # -----------------
        T = dsc_df["Temperature_C"].values
        hf = dsc_df["HeatFlow_mW"].values
        window = 101 if len(hf) >= 101 else (len(hf)//2*2 + 1)
        hf_s = savgol_filter(hf, window_length=window, polyorder=3)

        # Tg
        mask_tg = (T >= 80) & (T <= 200)
        dHdT = np.gradient(hf_s, T)
        idx_tg = np.argmax(np.abs(dHdT[mask_tg]))
        Tg = T[mask_tg][idx_tg]

        # Tc
        mask_tc = (T >= 200) & (T <= 360)
        peaks_tc, _ = find_peaks(hf_s[mask_tc], prominence=0.01, distance=50)
        Tc = T[mask_tc][peaks_tc[0]] if len(peaks_tc) > 0 else np.nan

        # Tm
        mask_tm = (T >= 330) & (T <= 420)
        peaks_tm, _ = find_peaks(-hf_s[mask_tm], prominence=0.01, distance=50)
        Tm = T[mask_tm][peaks_tm[0]] if len(peaks_tm) > 0 else np.nan

        # Enthalpi hesaplamaları (aynı fonksiyon mantığında)
        sample_mass_mg = 5.471
        heating_rate = 10.0  # sabit varsayıldı

        def integrate_peak(T, y, T_left, T_right, mass_mg, heat_rate_c_per_min):
            m = (T >= T_left) & (T <= T_right)
            Tw, yw = T[m], y[m]
            if len(Tw) < 3:
                return np.nan
            baseline = np.interp(Tw, [Tw[0], Tw[-1]], [yw[0], yw[-1]])
            ycorr = yw - baseline
            beta_c_per_s = heat_rate_c_per_min / 60.0
            area_mJ = np.trapz(ycorr, Tw) / beta_c_per_s
            area_J = area_mJ / 1000.0
            mass_g = mass_mg / 1000.0
            return area_J / mass_g if mass_g > 0 else np.nan

        dH_cc = integrate_peak(T, hf_s, Tc-15, Tc+15, sample_mass_mg, heating_rate)
        dH_m = integrate_peak(T, hf_s, Tm-15, Tm+15, sample_mass_mg, heating_rate)
        dH_melting = -dH_m if not np.isnan(dH_m) else np.nan
        cryst_pct = (dH_melting - dH_cc) / 130 * 100 if dH_melting and dH_cc else np.nan

        results = {
            "Tg (°C)": round(Tg, 1),
            "Tc (°C)": round(Tc, 1),
            "Tm (°C)": round(Tm, 1),
            "ΔH_cold_cryst (J/g)": round(dH_cc, 2),
            "ΔH_melting (J/g)": round(dH_melting, 2),
            "Crystallinity (%)": round(cryst_pct, 1)
        }

        st.subheader("📑 Calculated Results")
        st.json(results)

