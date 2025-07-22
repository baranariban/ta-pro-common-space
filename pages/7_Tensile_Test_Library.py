import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Tensile Test Library", page_icon="🔬", layout="wide")
st.title("🔬 Tensile Test Library")

# Define permanent upload folder
UPLOAD_DIR = "uploaded_tensile_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Load metadata
metadata_file = os.path.join(UPLOAD_DIR, "metadata.csv")
if os.path.exists(metadata_file):
    df_meta = pd.read_csv(metadata_file)
else:
    df_meta = pd.DataFrame(columns=["stored_filename", "original_filename", "user_given_name", "uploader", "timestamp"])
    df_meta.to_csv(metadata_file, index=False)

# File upload section
st.subheader("📤 Upload a new tensile test file")
uploaded_file = st.file_uploader("Upload Excel file", type=["csv", "xlsx"])
user_given_name = st.text_input("Enter a name for this file")

if "username" not in st.session_state:
    st.session_state.username = "unknown"  # yedek amaçlı

if st.button("Upload") and uploaded_file is not None and user_given_name:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    stored_filename = f"{timestamp}_{uploaded_file.name}"
    filepath = os.path.join(UPLOAD_DIR, stored_filename)

    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Add metadata
    new_entry = pd.DataFrame([{
        "stored_filename": stored_filename,
        "original_filename": uploaded_file.name,
        "user_given_name": user_given_name,
        "uploader": st.session_state.username,
        "timestamp": timestamp
    }])
    df_meta = pd.concat([df_meta, new_entry], ignore_index=True)
    df_meta.to_csv(metadata_file, index=False)
    st.success("File uploaded successfully. Please refresh the page.")

# Show uploaded files
st.subheader("📁 Uploaded Files")

def delete_file(stored_filename):
    os.remove(os.path.join(UPLOAD_DIR, stored_filename))
    df_meta.drop(df_meta[df_meta["stored_filename"] == stored_filename].index, inplace=True)
    df_meta.to_csv(metadata_file, index=False)
    st.experimental_rerun()

if len(df_meta) == 0:
    st.info("No files uploaded yet.")
else:
    for i, row in df_meta.iterrows():
        col1, col2, col3, col4, col5 = st.columns([3, 3, 2, 2, 1])
        col1.write(f"**Original:** {row['original_filename']}")
        col2.write(f"**Name:** {row['user_given_name']}")
        col3.write(f"**Uploader:** {row['uploader']}")
        col4.write(f"**Time:** {row['timestamp']}")
        if col5.button("Delete", key=row['stored_filename']):
            delete_file(row['stored_filename'])

import matplotlib.pyplot as plt
from io import StringIO

# Başlık
st.subheader("📊 Choose data to analyze")

# Kullanıcının verdiği adları seçenek olarak sun
selected_names = st.multiselect(
    label="Select one or more uploaded files to visualize",
    options=df_meta["user_given_name"].tolist()
)

# Her seçilen dosya için işlem yap
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

        # "Time measurement" satırını bul
        start_index = None
        for i, line in enumerate(lines):
            if "Time measurement" in line:
                start_index = i
                break

        if start_index is None:
            st.warning(f"⚠️ No data block found in file: {file_info['original_filename']}")
            continue

        # Tabloyu ayır ve başlık satırını ayır
        table_lines = lines[start_index:]
        df_table = pd.read_csv(StringIO("".join(table_lines)))
        df_clean = df_table[1:].copy()
        df_clean.columns = df_table.iloc[0]
        df_clean.columns = df_clean.columns.str.strip()

        # Sabit kolon adları
        df_clean.columns = ['Time_s', 'Extension_mm', 'Force_N', 'Strain_1', 'Strain_2', 'Stress_MPa']

        # Sayısal dönüştürme
        df_clean["Strain_2"] = pd.to_numeric(df_clean["Strain_2"], errors="coerce")
        df_clean["Stress_MPa"] = pd.to_numeric(df_clean["Stress_MPa"], errors="coerce")

        # Son tabloyu oluştur
        df_result = df_clean[["Strain_2", "Stress_MPa"]].copy()
        df_result = df_result.rename(columns={"Strain_2": "Strain (%)", "Stress_MPa": "Stress (MPa)"})

        # Gösterim
        st.markdown(f"### 📄 Data from: *{name}*")
        st.dataframe(df_result)

        # Grafik
        fig, ax = plt.subplots()
        ax.plot(df_result["Strain (%)"], df_result["Stress (MPa)"], label=name)
        ax.set_xlabel("Strain (%)")
        ax.set_ylabel("Stress (MPa)")
        ax.set_title(f"Stress-Strain Curve: {name}")
        ax.legend()
        st.pyplot(fig)

    except Exception as e:
        st.error(f"❌ Error reading file '{file_info['original_filename']}': {e}")

