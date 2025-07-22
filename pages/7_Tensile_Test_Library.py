import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import StringIO, BytesIO
import os
import base64

st.set_page_config(page_title="Tensile Test Library", page_icon="🔬", layout="wide")
st.title("🔬 Tensile Test Library")

UPLOAD_DIR = "uploaded_tensile_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)
metadata_file = os.path.join(UPLOAD_DIR, "metadata.csv")

if os.path.exists(metadata_file):
    df_meta = pd.read_csv(metadata_file)
else:
    df_meta = pd.DataFrame(columns=["stored_filename", "original_filename", "user_given_name", "uploader", "timestamp"])
    df_meta.to_csv(metadata_file, index=False)

# Başlık
st.subheader("📊 Choose data to analyze")

selected_names = st.multiselect(
    label="Select one or more uploaded files to visualize",
    options=df_meta["user_given_name"].tolist()
)

combined_fig, combined_ax = plt.subplots()
combined_ax.set_xlabel("Strain (%)")
combined_ax.set_ylabel("Stress (MPa)")
combined_ax.set_title("Stress-Strain Curves")

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

        # GÖSTER
        st.markdown(f"### 📄 Data from: *{name}*")
        st.dataframe(df_result)

        # GRAFİK
        fig, ax = plt.subplots()
        ax.plot(df_result["Strain (%)"], df_result["Stress (MPa)"], label=name)
        ax.set_xlabel("Strain (%)")
        ax.set_ylabel("Stress (MPa)")
        ax.set_title(f"Stress-Strain Curve: {name}")
        st.pyplot(fig)

        # BİREYSEL PNG İNDİR
        png_buffer = BytesIO()
        fig.savefig(png_buffer, format="png")
        b64_png = base64.b64encode(png_buffer.getvalue()).decode()
        href_png = f'<a href="data:image/png;base64,{b64_png}" download="{name}_plot.png">📥 Download PNG</a>'
        st.markdown(href_png, unsafe_allow_html=True)

        # EXCEL İNDİR
        excel_buffer = BytesIO()
        df_result.to_excel(excel_buffer, index=False, engine='openpyxl')
        b64_excel = base64.b64encode(excel_buffer.getvalue()).decode()
        href_excel = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64_excel}" download="{name}_data.xlsx">📥 Download Excel</a>'
        st.markdown(href_excel, unsafe_allow_html=True)

        # ORTAK GRAFİĞE EKLE
        combined_ax.plot(df_result["Strain (%)"], df_result["Stress (MPa)"], label=name)

    except Exception as e:
        st.error(f"❌ Error in file '{file_info['original_filename']}': {e}")

# Combined plot
if selected_names:
    combined_ax.legend()
    st.markdown("### 📈 Combined Stress-Strain Graph")
    st.pyplot(combined_fig)

    combined_png_buf = BytesIO()
    combined_fig.savefig(combined_png_buf, format="png")
    b64_combined = base64.b64encode(combined_png_buf.getvalue()).decode()
    combined_href = f'<a href="data:image/png;base64,{b64_combined}" download="combined_stress_strain.png">📥 Download Combined PNG</a>'
    st.markdown(combined_href, unsafe_allow_html=True)
