import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import StringIO, BytesIO
import os
import base64
from datetime import datetime

# ============================
# Page & Auth
# ============================
st.set_page_config(page_title="Tensile Test Library", page_icon="🔬", layout="wide")

if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("🔒 You must be logged in to access this page.")
    st.stop()

st.title("🔬 Tensile Test Library")

# ============================
# Persistent storage
# ============================
UPLOAD_DIR = "uploaded_tensile_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)
METADATA_PATH = os.path.join(UPLOAD_DIR, "metadata.csv")

if os.path.exists(METADATA_PATH):
    df_meta = pd.read_csv(METADATA_PATH)
else:
    df_meta = pd.DataFrame(columns=[
        "stored_filename", "original_filename", "user_given_name", "uploader", "timestamp"
    ])
    df_meta.to_csv(METADATA_PATH, index=False)

# ============================
# Helpers
# ============================
def _safe_filename(name: str) -> str:
    return "".join([c for c in name if c.isalnum() or c in (" ", ".", "_", "-")]).strip()


def _parse_csv_with_time_measurement(filepath: str) -> pd.DataFrame:
    """Reads CSV, finds 'Time measurement' header line, parses the table from there,
    and returns a DataFrame with columns renamed to a standard set where available.

    The plotting/metrics use only two columns ultimately:
      - Strain (%)   (mapped from Strain_2)
      - Stress (MPa) (mapped from Stress_MPa)
    """
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    start_idx = 0
    for i, line in enumerate(lines):
        if "Time measurement" in line:
            start_idx = i
            break

    table_text = "".join(lines[start_idx:])
    df = pd.read_csv(StringIO(table_text))

    # Bazı cihaz çıktılarında ilk satır tekrar başlık olabilir
    if df.shape[0] > 1 and any(isinstance(x, str) and x.strip().lower() == "time measurement" for x in df.iloc[0]):
        new_cols = df.iloc[0].astype(str).str.strip().tolist()
        df = df[1:].copy()
        df.columns = new_cols

    # Standart isimler (varsa)
    rename_map = {
        "Time measurement": "Time_s",
        "Extension": "Extension_mm",
        "Force": "Force_N",
        "Strain 1": "Strain_1",
        "Strain 2": "Strain_2",
        "Stress": "Stress_MPa",
    }

    for old, new in rename_map.items():
        if old in df.columns:
            df = df.rename(columns={old: new})

    # Grafikte kullanılacak iki kolonun adını sonrasında standardize edeceğiz
    # (veriyi TEMİZLEMEDEN, doğrudan mevcut değerleri kullanacağız)
    return df


def save_metadata(dfm: pd.DataFrame):
    dfm.to_csv(METADATA_PATH, index=False)

# ============================
# Upload section
# ============================
st.subheader("📤 Upload a new tensile test file")

uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx", "xls"])
user_given_name = st.text_input("Enter a name for this file", placeholder="e.g., PEKK_XZ_1")
uploader = st.session_state.get("username", "unknown")

if st.button("Upload", type="primary"):
    if not uploaded_file:
        st.warning("Please select a file.")
    elif not user_given_name.strip():
        st.warning("Please enter a name for this file.")
    else:
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        cleaned_original = _safe_filename(uploaded_file.name)
        stored_filename = f"{ts}_{cleaned_original}"
        filepath = os.path.join(UPLOAD_DIR, stored_filename)
        with open(filepath, "wb") as f:
            f.write(uploaded_file.getbuffer())

        df_meta = pd.concat([
            df_meta,
            pd.DataFrame([{
                "stored_filename": stored_filename,
                "original_filename": cleaned_original,
                "user_given_name": user_given_name.strip(),
                "uploader": uploader,
                "timestamp": ts
            }])
        ], ignore_index=True)
        save_metadata(df_meta)
        st.success("✅ File uploaded successfully. Please refresh if the list doesn't update.")
        st.rerun()

# ============================
# Uploaded files list & delete
# ============================
st.subheader("📁 Uploaded Files")

if df_meta.empty:
    st.info("No files uploaded yet.")
else:
    df_view = df_meta.copy()
    df_view["uploaded_at"] = pd.to_datetime(df_view["timestamp"], format="%Y%m%d%H%M%S", errors="coerce")
    df_view = df_view.sort_values("uploaded_at", ascending=False)

    df_view_display = df_view[["user_given_name", "original_filename", "uploader", "uploaded_at"]].rename(columns={
        "user_given_name": "Name",
        "original_filename": "Original File",
        "uploader": "Uploader",
        "uploaded_at": "Uploaded At"
    })

    st.dataframe(df_view_display, use_container_width=True)

    st.markdown("#### Manage files")
    for i, row in df_view.iterrows():
        c1, c2, c3, c4, c5 = st.columns([3, 3, 2, 2, 1])
        c1.write(f"**{row['user_given_name']}**")
        c2.write(row["original_filename"])
        c3.write(row["uploader"])
        c4.write(row["uploaded_at"])
        if c5.button("❌ Delete", key=f"del_{row['stored_filename']}"):
            path = os.path.join(UPLOAD_DIR, row["stored_filename"])
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                st.error(f"File remove error: {e}")
            df_meta = df_meta[df_meta["stored_filename"] != row["stored_filename"]].reset_index(drop=True)
            save_metadata(df_meta)
            st.success(f"Deleted {row['user_given_name']}")
            st.rerun()

# ============================
# Selection & Analysis
# ============================
st.subheader("📊 Choose data to analyze")

name_options = df_meta["user_given_name"].tolist()
selected_names = st.multiselect("Select one or more uploaded files to visualize", options=name_options)

combined_fig, combined_ax = plt.subplots()
combined_ax.set_xlabel("Strain (%)")
combined_ax.set_ylabel("Stress (MPa)")
combined_ax.set_title("Combined Stress-Strain Curves")

for name in selected_names:
    file_row = df_meta[df_meta["user_given_name"] == name]
    if file_row.empty:
        st.warning(f"Metadata not found for: {name}")
        continue

    file_info = file_row.iloc[0]
    path = os.path.join(UPLOAD_DIR, file_info["stored_filename"])

    ext = os.path.splitext(path)[1].lower()

    try:
        if ext == ".csv":
            df = _parse_csv_with_time_measurement(path)
        else:
            st.warning(f"{name}: Only CSV is analyzed for now. Excel display disabled.")
            continue

        # Bu aşamada veriyi TEMİZLEMİYORUZ.
        # Sadece mevcut sütunlarla çalışıp iki kolon çıkartıyoruz.
        if "Strain_2" not in df.columns or "Stress_MPa" not in df.columns:
            st.error(f"{name}: Required columns not found (need 'Strain 2' and 'Stress').")
            continue

        # Standart kolon isimleri
        df_result = df[["Strain_2", "Stress_MPa"]].copy()
        df_result = df_result.rename(columns={"Strain_2": "Strain (%)", "Stress_MPa": "Stress (MPa)"})

        # Tablo göster
        st.markdown(f"### 📄 Data from: *{name}*")
        st.dataframe(df_result, use_container_width=True)

        # Grafik
        fig, ax = plt.subplots()
        ax.plot(df_result["Strain (%)"], df_result["Stress (MPa)"], label=name)
        ax.set_xlabel("Strain (%)")
        ax.set_ylabel("Stress (MPa)")
        ax.set_title(f"Stress-Strain Curve: {name}")
        st.pyplot(fig)

        # --- İSTENEN METRİKLER (temizleme YOK) ---
        # Tensile strength (UTS) = Stress (MPa) kolonunun maksimumu
        try:
            uts = float(df_result["Stress (MPa)"].max())
        except Exception:
            uts = None

        # Elongation at break (%) = Veri setindeki SON satırın Strain (%) değeri
        try:
            elong_break = float(df_result["Strain (%)"].iloc[-1])
        except Exception:
            elong_break = None

        # Metin olarak grafiğin ALTINA yaz
        uts_txt = f"{uts:.3f} MPa" if uts is not None else "N/A"
        eb_txt = f"{elong_break:.3f} %" if elong_break is not None else "N/A"
        st.markdown(f"**Tensile strength (UTS):** {uts_txt}")
        st.markdown(f"**Elongation at break:** {eb_txt}")

        # Tekil PNG indir
        png_buf = BytesIO()
        fig.savefig(png_buf, format="png", bbox_inches="tight")
        b64_png = base64.b64encode(png_buf.getvalue()).decode()
        st.markdown(
            f'<a href="data:image/png;base64,{b64_png}" download="{name}_plot.png">📥 Download PNG</a>',
            unsafe_allow_html=True
        )

        # Tekil Excel indir
        xls_buf = BytesIO()
        df_result.to_excel(xls_buf, index=False, engine="openpyxl")
        b64_xls = base64.b64encode(xls_buf.getvalue()).decode()
        st.markdown(
            f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64_xls}" download="{name}_data.xlsx">📥 Download Excel</a>',
            unsafe_allow_html=True
        )

        # Combined grafiğe ekle
        combined_ax.plot(df_result["Strain (%)"], df_result["Stress (MPa)"], label=name)

    except Exception as e:
        st.error(f"❌ Error in file '{file_info['original_filename']}': {e}")

# ============================
# Combined graph
# ============================
if selected_names:
    combined_ax.legend()
    st.markdown("### 📈 Combined Stress-Strain Graph")
    st.pyplot(combined_fig)

    c_png_buf = BytesIO()
    combined_fig.savefig(c_png_buf, format="png", bbox_inches="tight")
    b64_cpng = base64.b64encode(c_png_buf.getvalue()).decode()
    st.markdown(
        f'<a href="data:image/png;base64,{b64_cpng}" download="combined_stress_strain.png">📥 Download Combined PNG</a>',
        unsafe_allow_html=True
    )
