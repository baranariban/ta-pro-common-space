# 5_DSC_Library.py
import streamlit as st
import pandas as pd
import os
import datetime
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import savgol_filter, find_peaks

# ✅ Kullanıcı giriş kontrolü
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("🔒 You must be logged in to access this page.")
    st.stop()

st.set_page_config(page_title="DSC Library", page_icon="🔬", layout="wide")
st.title("🔬 DSC Library")

# Oturumdan kullanıcı adı çekiyoruz; görünmeyecek (sadece kayıtta tutulabilir)
current_user = st.session_state.get("username", "unknown")

# 📁 Kalıcı kayıt dosyaları
UPLOAD_DIR = "dsc_uploads"
META_FILE = "dsc_uploads_metadata.csv"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Metadata şeması (uploaded_by tutulabilir fakat GÖSTERİLMEYECEK)
META_COLUMNS = ["file_name", "custom_name", "uploaded_by", "upload_time"]

if os.path.exists(META_FILE):
    meta_df = pd.read_csv(META_FILE)
    # Eksik sütun varsa tamamla
    for col in META_COLUMNS:
        if col not in meta_df.columns:
            meta_df[col] = "" if col != "upload_time" else None
    meta_df = meta_df[META_COLUMNS]
else:
    meta_df = pd.DataFrame(columns=META_COLUMNS)

# =============================
# 1) DOSYA YÜKLEME
# =============================
st.subheader("📤 Upload DSC Raw Data")
uploaded_file = st.file_uploader("Upload your DSC .txt file", type=["txt"], key="dsc_uploader")
custom_name = st.text_input("Custom name for this file", key="dsc_custom_name")

if uploaded_file is not None and st.button("Save Upload", type="primary"):
    save_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    new_entry = {
        "file_name": uploaded_file.name,
        "custom_name": custom_name.strip() if custom_name else uploaded_file.name,
        "uploaded_by": current_user,  # kayıtta kalsın ama gösterilmeyecek
        "upload_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    meta_df = pd.concat([meta_df, pd.DataFrame([new_entry])], ignore_index=True)
    meta_df.to_csv(META_FILE, index=False)
    st.success(f"✅ File '{uploaded_file.name}' uploaded and saved.")
    st.rerun()

# =============================
# 2) YÜKLENEN DOSYALAR — TEK TABLO (SİLİNEBİLİR)
# =============================
st.subheader("📂 Uploaded DSC Files")

if meta_df.empty:
    st.info("No files uploaded yet.")
else:
    # Sadece görünsün istenen sütunlar (uploaded_by YOK)
    view_df = meta_df[["file_name", "custom_name", "upload_time"]].copy()

    # Başlık satırı
    hdr = st.columns([5, 5, 4, 2])
    hdr[0].markdown("**File Name**")
    hdr[1].markdown("**Custom Name**")
    hdr[2].markdown("**Upload Time**")
    hdr[3].markdown("**Delete**")

    # Satırlar (TEK tablo görünümünde)
    for idx, row in view_df.reset_index().iterrows():
        cols = st.columns([5, 5, 4, 2])
        cols[0].write(row["file_name"])
        cols[1].write(row["custom_name"])
        cols[2].write(row["upload_time"])
        if cols[3].button("🗑️ Delete", key=f"del_{row['file_name']}"):
            # Fiziksel dosyayı sil
            try:
                fp = os.path.join(UPLOAD_DIR, row["file_name"])
                if os.path.exists(fp):
                    os.remove(fp)
            except Exception as e:
                st.error(f"File delete error: {e}")

            # Metadata'dan çıkar
            try:
                mask = (meta_df["file_name"] == row["file_name"]) & (meta_df["custom_name"] == row["custom_name"])
                meta_df = meta_df.loc[~mask].reset_index(drop=True)
                meta_df.to_csv(META_FILE, index=False)
                st.success(f"Deleted: {row['file_name']}")
            except Exception as e:
                st.error(f"Metadata update error: {e}")

            st.rerun()

# =============================
# 3) DOSYA SEÇİMİ + GÖRÜNTÜLEME
# =============================
if not meta_df.empty:
    st.markdown("---")
    st.subheader("🔎 Analyze a File")

    # Kullanıcı pohodaki adıyla seçsin
    selected_custom = st.selectbox("Select a file to analyze", meta_df["custom_name"].tolist())
    file_row = meta_df.loc[meta_df["custom_name"] == selected_custom].iloc[0]
    file_path = os.path.join(UPLOAD_DIR, file_row["file_name"])

    if not os.path.exists(file_path):
        st.error("Selected file is missing on disk.")
        st.stop()

    # -----------------
    # RAW DATA OKUMA
    # -----------------
    # Bazı DSC txt'lerinde header uzun olabilir; deneyimde 56. satırdan başlatılmıştı.
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
        # Bilimsel sütun adlarıyla DataFrame döndür
        df = pd.DataFrame(data, columns=["Time (min)", "Temperature (°C)", "Heat Flow (mW)"])
        return df

    dsc_df = load_dsc_txt(file_path, header_skip=56)

    st.markdown("**📋 Raw Data**")
    st.dataframe(dsc_df, use_container_width=True)

    # -----------------
    # GRAFİK
    # -----------------
    st.subheader("📊 DSC Curve")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(dsc_df["Temperature (°C)"], dsc_df["Heat Flow (mW)"], label=file_row["custom_name"])
    ax.set_xlabel("Temperature (°C)")
    ax.set_ylabel("Heat Flow (mW)")
    ax.legend()
    ax.grid(True)
    st.pyplot(fig)

    # -----------------
    # ANALİZ (Tg, Tc, Tm, ΔH, Kristallik)
    # -----------------
    if len(dsc_df) >= 5:
        T = dsc_df["Temperature (°C)"].values
        hf = dsc_df["Heat Flow (mW)"].values

        # Smoothing
        window = 101 if len(hf) >= 101 else (max(3, (len(hf) // 2) * 2 + 1))
        hf_s = savgol_filter(hf, window_length=window, polyorder=3)

        # Tg (eğim değişimi ~80–200 °C aralığında)
        mask_tg = (T >= 80) & (T <= 200)
        Tg = np.nan
        try:
            dHdT = np.gradient(hf_s, T)
            if mask_tg.any():
                idx_tg = np.argmax(np.abs(dHdT[mask_tg]))
                Tg = float(T[mask_tg][idx_tg])
        except Exception:
            Tg = np.nan

        # Tc (ekzotermik pik ~200–360 °C)
        Tc = np.nan
        try:
            mask_tc = (T >= 200) & (T <= 360)
            if mask_tc.any():
                peaks_tc, _ = find_peaks(hf_s[mask_tc], prominence=0.01, distance=50)
                if len(peaks_tc) > 0:
                    Tc = float(T[mask_tc][peaks_tc[0]])
        except Exception:
            Tc = np.nan

        # Tm (endotermik pik ~330–420 °C)
        Tm = np.nan
        try:
            mask_tm = (T >= 330) & (T <= 420)
            if mask_tm.any():
                peaks_tm, _ = find_peaks(-hf_s[mask_tm], prominence=0.01, distance=50)
                if len(peaks_tm) > 0:
                    Tm = float(T[mask_tm][peaks_tm[0]])
        except Exception:
            Tm = np.nan

        # Enthalpi (J/g) hesapları
        sample_mass_mg = 5.471      # gerekirse UI'dan parametreleştirilebilir
        heating_rate = 10.0         # °C/min varsayımı

        def integrate_peak(Tv, yv, T_left, T_right, mass_mg, heat_rate_c_per_min):
            if np.isnan(T_left) or np.isnan(T_right):
                return np.nan
            m = (Tv >= T_left) & (Tv <= T_right)
            Tw, yw = Tv[m], yv[m]
            if len(Tw) < 3:
                return np.nan
            # Baseline: uçları birleştir
            baseline = np.interp(Tw, [Tw[0], Tw[-1]], [yw[0], yw[-1]])
            ycorr = yw - baseline
            beta_c_per_s = heat_rate_c_per_min / 60.0
            # ∫(mW) dT  / (°C/s)  => mJ
            area_mJ = np.trapz(ycorr, Tw) / beta_c_per_s
            area_J = area_mJ / 1000.0
            mass_g = mass_mg / 1000.0
            return area_J / mass_g if mass_g > 0 else np.nan

        dH_cc = integrate_peak(T, hf_s, Tc - 15, Tc + 15, sample_mass_mg, heating_rate) if not np.isnan(Tc) else np.nan
        dH_m  = integrate_peak(T, hf_s, Tm - 15, Tm + 15, sample_mass_mg, heating_rate) if not np.isnan(Tm) else np.nan

        # Erime endotermik (grafikte aşağı yönde): işaret düzeltme
        dH_melting = -dH_m if not np.isnan(dH_m) else np.nan

        # ΔH_fus° (PEKK/PEEK için yaklaşık 130 J/g) üzerinden kristallik
        cryst_pct = np.nan
        if not np.isnan(dH_melting) and not np.isnan(dH_cc):
            cryst_pct = (dH_melting - dH_cc) / 130.0 * 100.0

        # ======= SONUÇ GÖSTERİMİ: METRIC KARTLAR =======
        st.subheader("📑 Calculated Results")

        def fmt(val, unit=""):
            if val is None or (isinstance(val, float) and np.isnan(val)):
                return "—"
            return f"{val} {unit}".strip()

        # Kartlar
        c1, c2, c3 = st.columns(3)
        c1.metric("Tg", fmt(None if np.isnan(Tg) else round(Tg, 1), "°C"))
        c2.metric("Tc", fmt(None if np.isnan(Tc) else round(Tc, 1), "°C"))
        c3.metric("Tm", fmt(None if np.isnan(Tm) else round(Tm, 1), "°C"))

        c4, c5, c6 = st.columns(3)
        c4.metric("ΔH (cold crystallization)", fmt(None if np.isnan(dH_cc) else round(dH_cc, 2), "J/g"))
        c5.metric("ΔH (melting)", fmt(None if np.isnan(dH_melting) else round(dH_melting, 2), "J/g"))
        c6.metric("Crystallinity", fmt(None if np.isnan(cryst_pct) else round(cryst_pct, 1), "%"))

    else:
        st.warning("Not enough data points to analyze.")

