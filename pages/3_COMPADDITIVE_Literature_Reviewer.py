import streamlit as st
import pandas as pd
import os
from datetime import datetime
import base64
from PIL import Image

st.set_page_config(page_title="COMPADDITIVE Literature Reviewer", layout="wide")

st.title("📚 COMPADDITIVE Literature Reviewer")

# 📂 Kalıcı klasör & veri yolları
UPLOAD_FOLDER = "lit_reviewer_files_compadditive"
METADATA_FILE = os.path.join(UPLOAD_FOLDER, "file_metadata.csv")

# 🧪 Giriş yapan kullanıcı
if "username" not in st.session_state:
    st.error("Please log in first.")
    st.stop()

current_user = st.session_state["username"]

# 📁 Klasör yoksa oluştur
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 📊 Metadata yükle veya oluştur
if os.path.exists(METADATA_FILE):
    metadata_df = pd.read_csv(METADATA_FILE)
else:
    metadata_df = pd.DataFrame(columns=["original_filename", "user_given_name", "description", "stored_filename", "uploader", "upload_time"])

# 🔼 Dosya yükleme
st.subheader("Upload a new file")
uploaded_file = st.file_uploader("Choose file", type=["pdf", "png", "jpg", "jpeg", "xlsx", "xls", "docx", "pptx"], label_visibility="collapsed")
user_given_name = st.text_input("Enter a title for this file")
user_description = st.text_area("Enter a description for this file")
if st.button("Upload") and uploaded_file and user_given_name:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    stored_filename = f"{timestamp}_{uploaded_file.name}"
    file_path = os.path.join(UPLOAD_FOLDER, stored_filename)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.read())

    new_entry = {
        "original_filename": uploaded_file.name,
        "user_given_name": user_given_name,
        "description": user_description,
        "stored_filename": stored_filename,
        "uploader": current_user,
        "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    metadata_df = pd.concat([metadata_df, pd.DataFrame([new_entry])], ignore_index=True)
    metadata_df.to_csv(METADATA_FILE, index=False)
    st.success("File uploaded successfully.")
    st.rerun()

# 📄 Yüklenen dosyaları göster
st.subheader("📂 Uploaded Files")

if metadata_df.empty:
    st.info("No files uploaded yet.")
else:
    for i, row in metadata_df.iterrows():
        file_path = os.path.join(UPLOAD_FOLDER, row["stored_filename"])
        cols = st.columns([2, 2, 3, 2, 2, 1, 1, 1])
        with cols[0]: st.markdown(f"📄 **Original:** {row['original_filename']}")
        with cols[1]: st.markdown(f"🏷️ **Title:** {row['user_given_name']}")
        with cols[2]: st.markdown(f"📜 **Description:** {row['description']}")
        with cols[3]: st.markdown(f"👭 **Uploader:** {row['uploader']}")
        with cols[4]: st.markdown(f"🕒 **Date:** {row['upload_time']}")

        with cols[5]:
            if st.button("❌", key=f"delete_{i}"):
                os.remove(file_path)
                metadata_df = metadata_df.drop(i).reset_index(drop=True)
                metadata_df.to_csv(METADATA_FILE, index=False)
                st.success("File deleted.")
                st.rerun()

        with cols[6]:
            with open(file_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
                href = f'<a href="data:application/octet-stream;base64,{b64}" download="{row["original_filename"]}">👅</a>'
                st.markdown(href, unsafe_allow_html=True)

        with cols[7]:
            if st.button("👁️", key=f"view_{i}"):
                st.markdown(f"### 👁️ Preview: {row['user_given_name']}")
                ext = row['stored_filename'].split('.')[-1].lower()
                if ext in ['jpg', 'jpeg', 'png']:
                    try:
                        image = Image.open(file_path)
                        st.image(image, caption=row["user_given_name"], use_column_width=True)
                    except:
                        st.warning("⚠️ Unable to display image.")
                else:
                    st.warning("🔒 Preview not available for this file type.")
