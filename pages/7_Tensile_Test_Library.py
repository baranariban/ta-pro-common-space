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
