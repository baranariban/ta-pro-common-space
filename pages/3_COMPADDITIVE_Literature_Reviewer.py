import streamlit as st
import pandas as pd
import os
from datetime import datetime
from io import BytesIO
import base64

st.set_page_config(page_title="Literature Reviewer", page_icon="📚", layout="wide")
st.title("📚 COMPADDITIVE Literature Reviewer")

UPLOAD_DIR = "uploaded_literature_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)
metadata_file = os.path.join(UPLOAD_DIR, "metadata.csv")

# Metadata dosyasını oku/yoksa oluştur
if os.path.exists(metadata_file):
    df_meta = pd.read_csv(metadata_file)
else:
    df_meta = pd.DataFrame(columns=[
        "stored_filename", "original_filename", "user_given_name", "description", "uploader", "timestamp"
    ])
    df_meta.to_csv(metadata_file, index=False)

# 🔼 Dosya yükleme alanı
st.subheader("📤 Upload a new file")
uploaded_file = st.file_uploader(
    "Supported: PDF, JPG, PNG, XLSX, DOCX, PPTX",
    type=["pdf", "jpg", "jpeg", "png", "xlsx", "docx", "pptx"]
)
user_given_name = st.text_input("Enter a title for this file")
description = st.text_area("Enter a short description")

if "username" not in st.session_state:
    st.session_state.username = "unknown"

if st.button("Upload") and uploaded_file and user_given_name:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stored_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uploaded_file.name}"
    filepath = os.path.join(UPLOAD_DIR, stored_filename)

    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())

    new_entry = pd.DataFrame([{
        "stored_filename": stored_filename,
        "original_filename": uploaded_file.name,
        "user_given_name": user_given_name,
        "description": description,
        "uploader": st.session_state.username,
        "timestamp": timestamp
    }])
    df_meta = pd.concat([df_meta, new_entry], ignore_index=True)
    df_meta.to_csv(metadata_file, index=False)
    st.success("✅ File uploaded successfully. Please refresh the page.")

# 🔽 Listeleme bölümü
st.subheader("📁 Uploaded Files")

if df_meta.empty:
    st.info("No files uploaded yet.")
else:
    for i, row in df_meta.iterrows():
        col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([2, 2, 3, 2, 2, 1, 1, 1])

        col1.markdown(f"📄 **Original:** {row['original_filename']}")
        col2.markdown(f"📝 **Title:** {row['user_given_name']}")
        col3.markdown(f"💬 **Description:** {row['description']}")
        col4.markdown(f"👤 **Uploader:** {row['uploader']}")
        col5.markdown(f"🕒 **Date:** {row['timestamp']}")
        file_path = os.path.join(UPLOAD_DIR, row["stored_filename"])

        # ❌ Silme butonu
        if col6.button("❌", key=f"delete_{i}"):
            if os.path.exists(file_path):
                os.remove(file_path)
            df_meta = df_meta.drop(i).reset_index(drop=True)
            df_meta.to_csv(metadata_file, index=False)
            st.success(f"Deleted: {row['user_given_name']}")
            st.experimental_rerun()

        # ⬇️ İndirme butonu
        with open(file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="{row["original_filename"]}">⬇️</a>'
            col7.markdown(href, unsafe_allow_html=True)

        # 👁️ Önizleme butonu
        if col8.button("👁️", key=f"view_{i}"):
            file_ext = row["stored_filename"].split(".")[-1].lower()
            st.markdown(f"### 👁️ Preview: {row['user_given_name']}")
            if file_ext == "pdf":
                with open(file_path, "rb") as f:
                    st.download_button("📥 Download", f, file_name=row["original_filename"])
                    st.pdf(f)
            elif file_ext in ["jpg", "jpeg", "png"]:
                st.image(file_path, caption=row["user_given_name"], use_column_width=True)
            else:
                st.info("📂 Preview not available for this file type.")
