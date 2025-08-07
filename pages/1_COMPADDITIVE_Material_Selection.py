import streamlit as st
import pandas as pd
from io import BytesIO

# ✅ Kullanıcı giriş kontrolü
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("🔒 You must be logged in to access this page.")
    st.stop()
  
st.set_page_config(page_title="COMPADDITIVE Material Selection", page_icon="🧪", layout="wide")
st.title("🧪 COMPADDITIVE Material Selection")

# 📋 Özellik listesi
properties = [
    "Coefficient of Thermal Expansion (CTE) (µstrain/°C)",
    "Cost (USD/kg)",
    "Heat Deflection Temperature A (1.8 MPa) (°C)",
    "Heat Deflection Temperature B (0.46 MPa) (°C)",
    "Interfacial Properties with Carbon Fiber (IFSS, MPa)",
    "Shrinkage (%)",
    "Tensile Strength (MPa)",
    "Flexural Modulus (GPa)",
    "Elongation At Break (%)",
    "Density (kg/m³)",
    "Glass Transition Temperature (°C)",
    "Melting Temperature (°C)",
    "Processing Temperature (°C)",
    "Injection Pressure (MPa)"
]

# 📁 Gömülü veri seti
if "datasets" not in st.session_state:
    st.session_state.datasets = {
        "PEEK UNFILLED": {
            "Coefficient of Thermal Expansion (CTE) (µstrain/°C)": (40, 60),
            "Cost (USD/kg)": (54.50, 81.75),
            "Heat Deflection Temperature A (1.8 MPa) (°C)": (140, 161),
            "Heat Deflection Temperature B (0.46 MPa) (°C)": (152, 210),
            "Interfacial Properties with Carbon Fiber (IFSS, MPa)": (80.0, 80.0),
            "Shrinkage (%)": (1.1, 1.1),
            "Tensile Strength (MPa)": (70, 100),
            "Flexural Modulus (GPa)": (3.7, 3.9),
            "Elongation At Break (%)": (1.7, 25.8),
            "Density (kg/m³)": (1270, 1320),
            "Glass Transition Temperature (°C)": (143, 143),
            "Melting Temperature (°C)": (334, 334),
            "Processing Temperature (°C)": (100, 290),
            "Injection Pressure (MPa)": (82.7, 124)
        }
    }

# 📤 Excel şablonu oluşturma fonksiyonu
def generate_excel_template():
    columns = ["Name"]
    for prop in properties:
        columns.append(f"{prop} min")
        columns.append(f"{prop} max")
    df_template = pd.DataFrame(columns=columns)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_template.to_excel(writer, index=False, sheet_name='Template')
    output.seek(0)
    return output

# ➕ Kullanıcıya seçim sun
option = st.radio("Choose how you'd like to proceed:", [
    "Use embedded dataset",
    "Add manual entry",
    "Upload dataset from Excel"
])

# 🔧 Manuel giriş
if option == "Add manual entry":
    new_entry = {}
    composite_name = st.text_input("Enter the name of the new composite")

    for prop in properties:
        col1, col2 = st.columns(2)
        with col1:
            min_val = st.number_input(f"Min {prop}", key=f"min_{prop}")
        with col2:
            max_val = st.number_input(f"Max {prop}", key=f"max_{prop}")
        new_entry[prop] = (min_val, max_val)

    if st.button("Add composite to dataset"):
        if composite_name and all(isinstance(val, tuple) for val in new_entry.values()):
            st.session_state.datasets[composite_name] = new_entry
            st.success(f"✅ {composite_name} added successfully.")

# 📥 Excel'den yükleme
elif option == "Upload dataset from Excel":
    st.info("""📄 Please download the template, fill in your data, and upload it back.

- Include values for all properties.
- Do **not change column names**.

📥 You can download the blank Excel file using the button below.""")

    st.download_button(
        label="📥 Download Excel Template",
        data=generate_excel_template(),
        file_name="composite_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    uploaded_file = st.file_uploader("Upload your completed Excel file here", type=["xlsx"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        for idx, row in df.iterrows():
            name = row["Name"]
            entry = {}
            for prop in properties:
                entry[prop] = (row[f"{prop} min"], row[f"{prop} max"])
            st.session_state.datasets[name] = entry
        st.success("✅ All composites from Excel uploaded successfully.")

