# 5_DSC_Library.py
import streamlit as st
import pandas as pd
import os
import datetime
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import savgol_filter, find_peaks
import io

# ✅ Giriş kontrolü (uygulamanızın mevcut auth akışına uygun)
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

    # Kullanıcı girişleri (dokümana uyum)
    sample_mass = st.number_input("Sample Mass (mg)", min_value=0.1, value=5.471, step=0.1, format="%.3f")
    material_type = st.selectbox("Material Type", ["Type I", "Type II", "Type III"])
    material_class = st.selectbox("Material", ["PEKK", "PEEK", "PPS", "PESU"])
    cycle = st.selectbox("Cycle", ["Heating 1", "Heating 2", "Cooling"])
    heating_rate = st.number_input("Heating Rate (°C/min)", min_value=0.1, value=10.0, step=0.1)

    # ΔH°fus referansları (J/g) — malzemeye göre
    DHfus_ref = {"PEKK": 130, "PEEK": 130, "PPS": 79, "PESU": None}

    # Dokümandaki tablo aralıkları sabitleri (örnekle doldurulmuş; kendi tablo değerlerinle güncelleyebilirsin)
    TABLE_RANGES = {
        "Tm": (330, 420),   # Table III: Melting region (heating)
        "Tc": (200, 360),   # Table IV: Crystallization region (cooling)
        "ΔHf": (330, 420),  # Table V: Heat of Fusion integration window
        "ΔHc": (200, 360),  # Table VI: Heat of Crystallization integration window
        "ΔHcc": (80, 330)   # Table VII: Cold Crystallization (Type III only, heating 1)
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

    # ---------- Raw Data + Excel indirme (openpyxl) ----------
    st.markdown("**📋 Raw Data**")
    st.dataframe(dsc_df, use_container_width=True)

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        dsc_df.to_excel(writer, index=False, sheet_name="DSC Raw Data")
    st.download_button(
        "⬇️ Download Raw Data (.xlsx)",
        data=excel_buffer.getvalue(),
        file_name=f"{file_row['custom_name']}_raw.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # ================== ANALİZ ==================
    if len(dsc_df) >= 5:
        T = dsc_df["Temperature (°C)"].values
        hf = dsc_df["Heat Flow (mW)"].values

        # Smoothing
        window = 101 if len(hf) >= 101 else max(3, (len(hf)//2)*2+1)
        hf_s = savgol_filter(hf, window_length=window, polyorder=3)

        Tg, Tc, Tm = np.nan, np.nan, np.nan
        dH_cc, dH_melting, dH_c = np.nan, np.nan, np.nan

        # ===== Tg (genel gözlem, türev maksimumu) =====
        try:
            dHdT = np.gradient(hf_s, T)
            idx = np.argmax(np.abs(dHdT))
            Tg = float(T[idx]) if 80 <= T[idx] <= 200 else np.nan
        except:
            pass

        # ===== Tc (Cooling) =====
        if cycle == "Cooling":
            lo, hi = TABLE_RANGES["Tc"]
            mask_tc = (T >= lo) & (T <= hi)
            try:
                peaks_tc, _ = find_peaks(hf_s[mask_tc], prominence=0.01, distance=50)
                if len(peaks_tc) > 0:
                    Tc = float(T[mask_tc][peaks_tc[0]])
                    # integral (ΔHc) — baseline düzeltmesi olmadan bölge integrali (tablo penceresi)
                    beta = heating_rate / 60.0
                    dH_c = np.trapz(hf_s[mask_tc], T[mask_tc]) / beta / (sample_mass / 1000.0)
            except:
                pass

        # ===== Tm (Heating 1 or 2; Type III → H1, Type I–II → H2) =====
        if (material_type == "Type III" and cycle == "Heating 1") or \
           (material_type in ["Type I", "Type II"] and cycle == "Heating 2"):
            lo, hi = TABLE_RANGES["Tm"]
            mask_tm = (T >= lo) & (T <= hi)
            try:
                peaks_tm, _ = find_peaks(-hf_s[mask_tm], prominence=0.01, distance=50)
                if len(peaks_tm) > 0:
                    Tm = float(T[mask_tm][peaks_tm[0]])
                    beta = heating_rate / 60.0
                    dH_melting = -np.trapz(hf_s[mask_tm], T[mask_tm]) / beta / (sample_mass / 1000.0)
            except:
                pass

        # ===== ΔHcc (Type III & Heating 1) =====
        if material_type == "Type III" and cycle == "Heating 1":
            lo, hi = TABLE_RANGES["ΔHcc"]
            mask_cc = (T >= lo) & (T <= hi)
            try:
                beta = heating_rate / 60.0
                dH_cc = np.trapz(hf_s[mask_cc], T[mask_cc]) / beta / (sample_mass / 1000.0)
            except:
                pass

        # ===== Kristallik (%) — malzemeye bağlı ΔH°fus =====
        cryst_pct = np.nan
        DHfus_ref_val = DHfus_ref[material_class]
        if DHfus_ref_val is not None and not np.isnan(dH_melting):
            cryst_pct = ((dH_melting - (0 if np.isnan(dH_cc) else dH_cc)) / DHfus_ref_val) * 100.0

        # ================== GRAFİK (işaretlemeli) ==================
        st.subheader("📊 DSC Curve with Analysis")
        fig, ax = plt.subplots(figsize=(9, 6))
        ax.plot(T, hf, color="gray", alpha=0.35, label="Raw")
        ax.plot(T, hf_s, label="Smoothed")

        # Tg çizgisi
        if not np.isnan(Tg):
            ax.axvline(Tg, color="orange", linestyle="--", linewidth=1.5, label=f"Tg = {round(Tg,1)} °C")

        # Tc çizgisi + gölgeli bölge
        if not np.isnan(Tc):
            ax.axvline(Tc, color="green", linestyle="--", linewidth=1.5, label=f"Tc = {round(Tc,1)} °C")
        lo_tc, hi_tc = TABLE_RANGES["Tc"]
        ax.fill_between(T, hf_s, 0, where=(T >= lo_tc) & (T <= hi_tc), color="green", alpha=0.15, label="Tc region")

        # Tm çizgisi + gölgeli bölge
        if not np.isnan(Tm):
            ax.axvline(Tm, color="red", linestyle="--", linewidth=1.5, label=f"Tm = {round(Tm,1)} °C")
        lo_tm, hi_tm = TABLE_RANGES["Tm"]
        ax.fill_between(T, hf_s, 0, where=(T >= lo_tm) & (T <= hi_tm), color="red", alpha=0.15, label="Tm region")

        # ΔHcc bölgesi (yalnız Type III & H1)
        if material_type == "Type III":
            lo_cc, hi_cc = TABLE_RANGES["ΔHcc"]
            ax.fill_between(T, hf_s, 0, where=(T >= lo_cc) & (T <= hi_cc), color="purple", alpha=0.12, label="Cold cryst.")

        ax.set_xlabel("Temperature (°C)")
        ax.set_ylabel("Heat Flow (mW)")
        ax.legend()
        ax.grid(True)

        # Analizli grafiği indir (PNG)
        png_buf = io.BytesIO()
        fig.savefig(png_buf, format="png", dpi=300, bbox_inches="tight")
        st.download_button(
            "⬇️ Download DSC Curve with Analysis (.png)",
            data=png_buf.getvalue(),
            file_name=f"{file_row['custom_name']}_curve_analysis.png",
            mime="image/png"
        )
        st.pyplot(fig)

        # ================== SONUÇ KARTLARI ==================
        st.subheader("📑 Calculated Results")
        def fmt(v, u=""):
            try:
                if v is None or np.isnan(v):
                    return "—"
            except:
                pass
            return f"{round(float(v), 2)} {u}".strip()

        c1, c2, c3 = st.columns(3)
        c1.metric("Tg", fmt(Tg, "°C"))
        c2.metric("Tc", fmt(Tc, "°C"))
        c3.metric("Tm", fmt(Tm, "°C"))

        c4, c5, c6 = st.columns(3)
        c4.metric("ΔHcc", fmt(dH_cc, "J/g") if material_type == "Type III" else "—")
        c5.metric("ΔHm", fmt(dH_melting, "J/g"))
        c6.metric("Crystallinity", fmt(cryst_pct, "%"))
