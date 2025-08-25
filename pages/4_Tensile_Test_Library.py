import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import StringIO, BytesIO
import os
import base64
from datetime import datetime

# 🔐 Kullanıcı giriş kontrolü
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("🔒 You must be logged in to access this page.")
    st.stop()

st.set_page_config(page_title="Tensile Test Library", page_icon="🔬", layout="wide")
st.title("🔬 Tensile Test Library")

# 📁 Kalıcı depolama
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

# 🔧 Yardımcılar
def _safe_filename(name: str) -> str:
    return "".join([c for c in name if c.isalnum() or c in (" ", ".", "_", "-")]).strip()

def _parse_csv_from_time_measurement(filepath: str) -> pd.DataFrame:
    """
    CSV dosyasında 'Time measurement' satırını bulur ve tablodan itibaren okur.
    Kolonları, varsa, aşağıdaki standart isimlere çevirir:
      Time measurement -> Time_s
      Extension        -> Extension_mm
      Force            -> Force_N
      Strain 1         -> Strain_1
      Strain 2         -> Strain_2
      Stress           -> Stress_MPa
    NOT: Herhangi bir veri temizliği YAPMIYOR.
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

    # Bazı cihaz çıktılarında ilk veri satırı tekrar başlık olabiliyor
    if df.shape[0] > 1 and any(isinstance(x, str) and x.strip().lower() == "time measurement" for x in df.iloc[0]):
        new_cols = df.iloc[0].astype(str).str.strip().tolist()
        df = df[1:].copy()
        df.columns = new_cols

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

    return df

def _save_metadata(dfm: pd.DataFrame):
    dfm.to_csv(METADATA_PATH, index=False)

# 🟦 Yükleme alanı
st.subheader("📤 Upload a new tensile test file")
uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])
user_given_name = st.text_input("Enter a name for this file", placeholder="e.g., PEKK_XZ_1")
uploader = st.session_state.get("username", "unknown")

if st.button("Upload", type="primary"):
    if not uploaded_file:
        st.warning("Please select a file.")
    elif not user_given_name.strip():
        st.warning("Please enter a name for this file.")
    else:
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        stored_filename = f"{ts}_{_safe_filename(uploaded_file.name)}"
        filepath = os.path.join(UPLOAD_DIR, stored_filename)
        with open(filepath, "wb") as f:
            f.write(uploaded_file.getbuffer())

        df_meta = pd.concat([
            df_meta,
            pd.DataFrame([{
                "stored_filename": stored_filename,
                "original_filename": _safe_filename(uploaded_file.name),
                "user_given_name": user_given_name.strip(),
                "uploader": uploader,
                "timestamp": ts
            }])
        ], ignore_index=True)
        _save_metadata(df_meta)
        st.success("✅ File uploaded successfully.")
        st.rerun()

# 📁 Yüklenen dosyalar listesi & silme
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
    for _, row in df_view.iterrows():
        c1, c2, c3, c4, c5 = st.columns([3, 3, 2, 2, 1])
        c1.write(f"**{row['user_given_name']}**")
        c2.write(row["original_filename"])
        c3.write(row["uploader"])
        c4.write(row["uploaded_at"])
        if c5.button("❌ Delete", key=f"del_{row['stored_filename']}"):
            p = os.path.join(UPLOAD_DIR, row["stored_filename"])
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception as e:
                st.error(f"File remove error: {e}")
            df_meta = df_meta[df_meta["stored_filename"] != row["stored_filename"]].reset_index(drop=True)
            _save_metadata(df_meta)
            st.success(f"Deleted {row['user_given_name']}")
            st.rerun()

# 📊 Seçim & Analiz
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

    info = file_row.iloc[0]
    path = os.path.join(UPLOAD_DIR, info["stored_filename"])
    ext = os.path.splitext(path)[1].lower()

    try:
        if ext == ".csv":
            df = _parse_csv_from_time_measurement(path)
        else:
            st.warning(f"{name}: Only CSV is analyzed for now. Excel display disabled.")
            continue

        # (Hiç veri temizliği yok) — Sadece iki kolon kullanılır:
        if "Strain_2" not in df.columns or "Stress_MPa" not in df.columns:
            st.error(f"{name}: Required columns not found (need 'Strain 2' and 'Stress').")
            continue

        df_result = df[["Strain_2", "Stress_MPa"]].copy()
        df_result = df_result.rename(columns={"Strain_2": "Strain (%)", "Stress_MPa": "Stress (MPa)"})

        # Tablo
        st.markdown(f"### 📄 Data from: *{name}*")
        st.dataframe(df_result, use_container_width=True)

        # Grafik
        fig, ax = plt.subplots()
        ax.plot(df_result["Strain (%)"], df_result["Stress (MPa)"], label=name)
        ax.set_xlabel("Strain (%)")
        ax.set_ylabel("Stress (MPa)")
        ax.set_title(f"Stress-Strain Curve: {name}")
        st.pyplot(fig)

        # ⬇️ SADECE İSTENEN İKİ METRİK (temizlik yok)
        uts = float(df_result["Stress (MPa)"].max()) if not df_result.empty else None
        elong_break = float(df_result["Strain (%)"].iloc[-1]) if not df_result.empty else None
        st.markdown(f"**Tensile strength (UTS):** {uts:.3f} MPa" if uts is not None else "**Tensile strength (UTS):** N/A")
        st.markdown(f"**Elongation at break:** {elong_break:.3f} %" if elong_break is not None else "**Elongation at break:** N/A")

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
        st.error(f"❌ Error in file '{info['original_filename']}': {e}")

# 📈 Combined grafik
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
