import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import StringIO, BytesIO
import os
import base64
from datetime import datetime

st.set_page_config(page_title="Tensile Test Library", page_icon="🔬", layout="wide")
st.title("🔬 Tensile Test Library")

# Klasör ve metadata ayarları
UPLOAD_DIR = "uploaded_tensile_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)
metadata_file = os.path.join(UPLOAD_DIR, "metadata.csv")

# Metadata dosyasını oku veya oluştur
if os.path.exists(metadata_file):
    df_meta = pd.read_csv(metadata_file)
else:
    df_meta = pd.DataFrame(columns=["stored_filename", "original_filename", "user_given_name", "uploader", "timestamp"])
    df_meta.to_csv(metadata_file, index=False)

# 🟦 YÜKLEME ALANI
st.subheader("📤 Upload a new tensile test file")

uploaded_file = st.file_uploader("Upload Excel file", type=["csv", "xlsx"])
user_given_name = st.text_input("Enter a name for this file")

if "username" not in st.session_state:
    st.session_state.username = "unknown"  # ya da baranariban gibi login'den gelen veri

if st.button("Upload") and uploaded_file and user_given_name:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    stored_filename = f"{timestamp}_{uploaded_file.name}"
    filepath = os.path.join(UPLOAD_DIR, stored_filename)

    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())

    new_entry = pd.DataFrame([{
        "stored_filename": stored_filename,
        "original_filename": uploaded_file.name,
        "user_given_name": user_given_name,
        "uploader": st.session_state.username,
        "timestamp": timestamp
    }])
    df_meta = pd.concat([df_meta, new_entry], ignore_index=True)
    df_meta.to_csv(metadata_file, index=False)
    st.success("✅ File uploaded successfully. Please refresh the page.")

# 🗂️ Mevcut dosyaların listesini göster
st.subheader("📁 Uploaded Files")

if df_meta.empty:
    st.info("No files uploaded yet.")
else:
    # Dosya tablosunu hazırla
    for i, row in df_meta.iterrows():
        col1, col2, col3, col4 = st.columns([3, 3, 2, 1])
        col1.markdown(f"📄 **Original file:** {row['original_filename']}")
        col2.markdown(f"📝 **Name given:** {row['user_given_name']}")
        col3.markdown(f"👤 **Uploader:** {row['uploader']}")

        if col4.button("❌ Delete", key=f"delete_{i}"):
            # Dosya silinsin
            file_to_delete = os.path.join(UPLOAD_DIR, row["stored_filename"])
            if os.path.exists(file_to_delete):
                os.remove(file_to_delete)

            df_meta = df_meta.drop(i).reset_index(drop=True)
            df_meta.to_csv(metadata_file, index=False)
            st.success(f"Deleted {row['user_given_name']}")
            st.rerun()

# 🟦 VERİ SEÇİMİ VE ANALİZ
st.subheader("📊 Choose data to analyze")

selected_names = st.multiselect(
    label="Select one or more uploaded files to visualize",
    options=df_meta["user_given_name"].tolist()
)

# Ortak grafik için hazırlık
combined_fig, combined_ax = plt.subplots()
combined_ax.set_xlabel("Strain (%)")
combined_ax.set_ylabel("Stress (MPa)")
combined_ax.set_title("Combined Stress-Strain Curves")

# Seçilen her dosya için tablo ve grafik göster
for name in selected_names:
    file_info = df_meta[df_meta["user_given_name"] == name].iloc[0]
    filepath = os.path.join(UPLOAD_DIR, file_info["stored_filename"])

    try:
        if filepath.endswith(".csv"):
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
        else:
            st.warning(f"📄 Excel files are not yet supported for this analysis.")
            continue

        # Verinin başladığı satırı bul
        start_index = next(i for i, line in enumerate(lines) if "Time measurement" in line)
        table_lines = lines[start_index:]
        df_table = pd.read_csv(StringIO("".join(table_lines)))
        df_clean = df_table[1:].copy()
        df_clean.columns = df_table.iloc[0]
        df_clean.columns = df_clean.columns.str.strip()
        df_clean.columns = ['Time_s', 'Extension_mm', 'Force_N', 'Strain_1', 'Strain_2', 'Stress_MPa']

        df_clean["Strain_2"] = pd.to_numeric(df_clean["Strain_2"], errors="coerce")
        df_clean["Stress_MPa"] = pd.to_numeric(df_clean["Stress_MPa"], errors="coerce")

        df_result = df_clean[["Strain_2", "Stress_MPa"]].copy()
        df_result = df_result.rename(columns={"Strain_2": "Strain (%)", "Stress_MPa": "Stress (MPa)"})

        # Tablo göster
        st.markdown(f"### 📄 Data from: *{name}*")
        st.dataframe(df_result)

        # Grafik oluştur
        fig, ax = plt.subplots()
        ax.plot(df_result["Strain (%)"], df_result["Stress (MPa)"], label=name)
        ax.set_xlabel("Strain (%)")
        ax.set_ylabel("Stress (MPa)")
        ax.set_title(f"Stress-Strain Curve: {name}")
        st.pyplot(fig)

        # PNG olarak indir
        png_buffer = BytesIO()
        fig.savefig(png_buffer, format="png")
        b64_png = base64.b64encode(png_buffer.getvalue()).decode()
        href_png = f'<a href="data:image/png;base64,{b64_png}" download="{name}_plot.png">📥 Download PNG</a>'
        st.markdown(href_png, unsafe_allow_html=True)

        # Excel olarak indir
        excel_buffer = BytesIO()
        df_result.to_excel(excel_buffer, index=False, engine='openpyxl')
        b64_excel = base64.b64encode(excel_buffer.getvalue()).decode()
        href_excel = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64_excel}" download="{name}_data.xlsx">📥 Download Excel</a>'
        st.markdown(href_excel, unsafe_allow_html=True)

        # Ortak grafiğe ekle
        combined_ax.plot(df_result["Strain (%)"], df_result["Stress (MPa)"], label=name)

    except Exception as e:
        st.error(f"❌ Error in file '{file_info['original_filename']}': {e}")

# 🟦 Combined grafik göster
if selected_names:
    combined_ax.legend()
    st.markdown("### 📈 Combined Stress-Strain Graph")
    st.pyplot(combined_fig)

    combined_png_buf = BytesIO()
    combined_fig.savefig(combined_png_buf, format="png")
    b64_combined = base64.b64encode(combined_png_buf.getvalue()).decode()
    combined_href = f'<a href="data:image/png;base64,{b64_combined}" download="combined_stress_strain.png">📥 Download Combined PNG</a>'
    st.markdown(combined_href, unsafe_allow_html=True)
