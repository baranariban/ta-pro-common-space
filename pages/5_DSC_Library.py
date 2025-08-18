# 5_DSC_Library.py
import streamlit as st
import pandas as pd
import os
import datetime
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import savgol_filter, find_peaks
import io

# ✅ Kullanıcı giriş kontrolü
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("🔒 You must be logged in to access this page.")
    st.stop()

st.set_page_config(page_title="DSC Library", page_icon="🔬", layout="wide")
st.title("🔬 DSC Library")

current_user = st.session_state.get("username", "unknown")

# 📁 Klasörler
UPLOAD_DIR = "dsc_uploads"
META_FILE = "dsc_uploads_metadata.csv"
os.makedirs(UPLOAD_DIR, exist_ok=True)

META_COLUMNS = ["file_name", "custom_name", "uploaded_by", "upload_time"]
if os.path.exists(META_FILE):
    meta_df = pd.read_csv(META_FILE)
    for col in META_COLUMNS:
        if col not in meta_df.columns:
            meta_df[col] = ""
    meta_df = meta_df[META_COLUMNS]
else:
    meta_df = pd.DataFrame(columns=META_COLUMNS)

# =============================
# 1) Dosya Yükleme
# =============================
st.subheader("📤 Upload DSC Raw Data")
uploaded_file = st.file_uploader("Upload your DSC .txt file", type=["txt"])
custom_name = st.text_input("Custom name for this file")

if uploaded_file is not None and st.button("Save Upload", type="primary"):
    save_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    new_entry = {
        "file_name": uploaded_file.name,
        "custom_name": custom_name.strip() if custom_name else uploaded_file.name,
        "uploaded_by": current_user,
        "upload_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    meta_df = pd.concat([meta_df, pd.DataFrame([new_entry])], ignore_index=True)
    meta_df.to_csv(META_FILE, index=False)
    st.success(f"✅ File '{uploaded_file.name}' uploaded and saved.")
    st.rerun()

# =============================
# 2) Yüklenen Dosyalar
# =============================
st.subheader("📂 Uploaded DSC Files")
if meta_df.empty:
    st.info("No files uploaded yet.")
else:
    hdr = st.columns([5, 5, 4, 2])
    hdr[0].markdown("**File Name**")
    hdr[1].markdown("**Custom Name**")
    hdr[2].markdown("**Upload Time**")
    hdr[3].markdown("**Delete**")
    for idx, row in meta_df.reset_index().iterrows():
        cols = st.columns([5, 5, 4, 2])
        cols[0].write(row["file_name"])
        cols[1].write(row["custom_name"])
        cols[2].write(row["upload_time"])
        if cols[3].button("🗑️ Delete", key=f"del_{row['file_name']}"):
            try:
                os.remove(os.path.join(UPLOAD_DIR, row["file_name"]))
            except:
                pass
            meta_df = meta_df.loc[meta_df["file_name"] != row["file_name"]].reset_index(drop=True)
            meta_df.to_csv(META_FILE, index=False)
            st.success(f"Deleted: {row['file_name']}")
            st.rerun()

# =============================
# 3) Analiz
# =============================
if not meta_df.empty:
    st.markdown("---")
    st.subheader("🔎 Analyze a File")

    selected_custom = st.selectbox("Select a file to analyze", meta_df["custom_name"].tolist())
    file_row = meta_df.loc[meta_df["custom_name"] == selected_custom].iloc[0]
    file_path = os.path.join(UPLOAD_DIR, file_row["file_name"])
    if not os.path.exists(file_path):
        st.error("File missing on disk.")
        st.stop()

    # Kullanıcı girişleri
    sample_mass = st.number_input("Sample Mass (mg)", min_value=0.1, value=5.471, step=0.1, format="%.3f")
    material_type = st.selectbox("Material Type", ["Type I", "Type II", "Type III"])
    material_class = st.selectbox("Material", ["PEKK", "PEEK", "PPS", "PESU"])
    cycle = st.selectbox("Cycle", ["Heating 1", "Heating 2", "Cooling"])
    heating_rate = st.number_input("Heating Rate (°C/min)", min_value=0.1, value=10.0, step=0.1)

    # ΔH°fus referansları (J/g)
    DHfus_ref = {"PEKK": 130, "PEEK": 130, "PPS": 79, "PESU": None}

    # Tablo aralıkları (örnek değerler, dokümandan adapte edilebilir)
    TABLE_RANGES = {
        "Tm": (330, 420),   # Table III
        "Tc": (200, 360),   # Table IV
        "ΔHf": (330, 420),  # Table V
        "ΔHc": (200, 360),  # Table VI
        "ΔHcc": (80, 330)   # Table VII (Type III only)
    }

    # Raw data okuma
    def load_dsc_txt(path, header_skip=56):
        with open(path, "r", encoding="latin1") as f:
            lines = f.readlines()
        data = []
        for line in lines[header_skip:]:
            parts = line.strip().split()
            if len(parts) == 3:
                try:
                    data.append([float(parts[0]), float(parts[1]), float(parts[2])])
                except:
                    pass
        return pd.DataFrame(data, columns=["Time (min)", "Temperature (°C)", "Heat Flow (mW)"])

    dsc_df = load_dsc_txt(file_path, header_skip=56)
    st.markdown("**📋 Raw Data**")
    st.dataframe(dsc_df, use_container_width=True)

    # 📥 Raw Data indir
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
        dsc_df.to_excel(writer, index=False, sheet_name="DSC Raw Data")
    st.download_button("⬇️ Download Raw Data (.xlsx)", excel_buffer.getvalue(),
                       file_name=f"{file_row['custom_name']}_raw.xlsx")

    # ================== ANALİZ ==================
    if len(dsc_df) >= 5:
        T = dsc_df["Temperature (°C)"].values
        hf = dsc_df["Heat Flow (mW)"].values
        window = 101 if len(hf) >= 101 else max(3, (len(hf)//2)*2+1)
        hf_s = savgol_filter(hf, window_length=window, polyorder=3)

        Tg, Tc, Tm, dH_cc, dH_melting, dH_c = np.nan, np.nan, np.nan, np.nan, np.nan, np.nan

        # Tg (genel gözlem)
        try:
            dHdT = np.gradient(hf_s, T)
            idx = np.argmax(np.abs(dHdT))
            Tg = float(T[idx]) if 80 <= T[idx] <= 200 else np.nan
        except: pass

        # Tc (Cooling)
        if cycle == "Cooling":
            rng = TABLE_RANGES["Tc"]
            mask = (T >= rng[0]) & (T <= rng[1])
            try:
                peaks_tc, _ = find_peaks(hf_s[mask], prominence=0.01, distance=50)
                if len(peaks_tc) > 0:
                    Tc = float(T[mask][peaks_tc[0]])
                    dH_c = np.trapz(hf_s[mask], T[mask])/(heating_rate/60)/(sample_mass/1000)
            except: pass

        # Tm (Heating 1 or 2)
        if (material_type == "Type III" and cycle == "Heating 1") or \
           (material_type in ["Type I", "Type II"] and cycle == "Heating 2"):
            rng = TABLE_RANGES["Tm"]
            mask = (T >= rng[0]) & (T <= rng[1])
            try:
                peaks_tm, _ = find_peaks(-hf_s[mask], prominence=0.01, distance=50)
                if len(peaks_tm) > 0:
                    Tm = float(T[mask][peaks_tm[0]])
                    dH_melting = -np.trapz(hf_s[mask], T[mask])/(heating_rate/60)/(sample_mass/1000)
            except: pass

        # ΔHcc (Type III, Heating 1)
        if material_type == "Type III" and cycle == "Heating 1":
            rng = TABLE_RANGES["ΔHcc"]
            mask = (T >= rng[0]) & (T <= rng[1])
            try:
                dH_cc = np.trapz(hf_s[mask], T[mask])/(heating_rate/60)/(sample_mass/1000)
            except: pass

        # Kristallik
        cryst_pct = np.nan
        DHfus_ref_val = DHfus_ref[material_class]
        if DHfus_ref_val is not None and not np.isnan(dH_melting):
            cryst_pct = ((dH_melting - (0 if np.isnan(dH_cc) else dH_cc)) / DHfus_ref_val) * 100

        # ======= GRAFİK =======
        st.subheader("📊 DSC Curve with Analysis")
        fig, ax = plt.subplots(figsize=(9, 6))
        ax.plot(T, hf, color="gray", alpha=0.4, label="Raw")
        ax.plot(T, hf_s, color="blue", label="Smoothed")

        # Tg çizgisi
        if not np.isnan(Tg):
            ax.axvline(Tg, color="orange", linestyle="--", label=f"Tg = {round(Tg,1)} °C")

        # Tc çizgisi + alan
        if not np.isnan(Tc):
            ax.axvline(Tc, color="green", linestyle="--", label=f"Tc = {round(Tc,1)} °C")
            ax.fill_between(T, hf_s, 0, where=(T>=TABLE_RANGES["Tc"][0]) & (T<=TABLE_RANGES["Tc"][1]),
                            color="green", alpha=0.2)

        # Tm çizgisi + alan
        if not np.isnan(Tm):
            ax.axvline(Tm, color="red", linestyle="--", label=f"Tm = {round(Tm,1)} °C")
            ax.fill_between(T, hf_s, 0, where=(T>=TABLE_RANGES["Tm"][0]) & (T<=TABLE_RANGES["Tm"][1]),
                            color="red", alpha=0.2)

        # ΔHcc alanı (Type III)
        if not np.isnan(dH_cc):
            ax.fill_between(T, hf_s, 0, where=(T>=TABLE_RANGES["ΔHcc"][0]) & (T<=TABLE_RANGES["ΔHcc"][1]),
                            color="purple", alpha=0.2, label="Cold Cryst.")

        ax.set_xlabel("Temperature (°C)")
        ax.set_ylabel("Heat Flow (mW)")
        ax.legend()
        ax.grid(True)

        png_buf = io.BytesIO()
        fig.savefig(png_buf, format="png", dpi=300, bbox_inches="tight")
        st.download_button("⬇️ Download DSC Curve with Analysis (.png)", png_buf.getvalue(),
                           file_name=f"{file_row['custom_name']}_curve_analysis.png", mime="image/png")
        st.pyplot(fig)

        # ======= SONUÇLAR =======
        st.subheader("📑 Calculated Results")
        def fmt(v, u=""): return "—" if np.isnan(v) else f"{round(v,2)} {u}"
        c1, c2, c3 = st.columns(3)
        c1.metric("Tg", fmt(Tg,"°C"))
        c2.metric("Tc", fmt(Tc,"°C"))
        c3.metric("Tm", fmt(Tm,"°C"))
        c4, c5, c6 = st.columns(3)
        c4.metric("ΔHcc", fmt(dH_cc,"J/g") if material_type=="Type III" else "—")
        c5.metric("ΔHm", fmt(dH_melting,"J/g"))
        c6.metric("Crystallinity", fmt(cryst_pct,"%"))
