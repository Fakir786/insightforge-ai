import io
import re
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Data Cleaning Studio",
    page_icon="🧹",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .block-container {padding-top: 2rem; padding-bottom: 3rem;}
    [data-testid="stMetric"] {background: #f4f7fb; padding: 16px; border-radius: 12px;}
    .hero {padding: 1.5rem 1.7rem; border-radius: 16px; background: linear-gradient(120deg,#102a43,#176b87); color: white; margin-bottom: 1.2rem;}
    .hero h1 {color: white; margin: 0 0 .35rem 0;}
    .hero p {color: #e6f4f7; margin: 0;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>🧹 Data Cleaning Studio</h1>
  <p>Upload a CSV or Excel file. Inspect data quality, clean your dataset, and download the result.</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("How it works")
    st.write("1. Upload a CSV or Excel file.")
    st.write("2. Review data quality checks.")
    st.write("3. Choose cleaning operations.")
    st.write("4. Download your cleaned file.")
    st.divider()
    st.caption("Privacy: files are processed in this app session and are not added to a public dataset.")

uploaded = st.file_uploader(
    "Choose a CSV or Excel file",
    type=["csv", "xlsx", "xls"],
    help="Supported formats: .csv, .xlsx and .xls. Maximum upload size depends on the hosting service.",
)

def load_csv(file):
    raw = file.getvalue()
    errors = []
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            return pd.read_csv(io.BytesIO(raw), encoding=encoding, sep=None, engine="python")
        except UnicodeDecodeError as exc:
            errors.append(str(exc))
    raise ValueError("Could not decode this CSV file. Save it as UTF-8 and upload again.")

def load_excel(file):
    excel = pd.ExcelFile(file)
    if len(excel.sheet_names) == 1:
        sheet = excel.sheet_names[0]
    else:
        sheet = st.selectbox("Select worksheet", excel.sheet_names)
    return pd.read_excel(file, sheet_name=sheet), sheet

def clean_column_name(value):
    value = str(value).strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "column"

if uploaded is None:
    st.info("Upload a file to begin. You will see a preview and data-quality report here.")
    st.subheader("What this tool checks")
    c1, c2, c3 = st.columns(3)
    c1.markdown("**Missing values**\n\nCounts empty cells in each column.")
    c2.markdown("**Duplicate rows**\n\nFinds repeated records.")
    c3.markdown("**Text consistency**\n\nFinds leading/trailing spaces and inconsistent column labels.")
    st.stop()

try:
    if uploaded.name.lower().endswith(".csv"):
        original_df = load_csv(uploaded)
        sheet_label = None
    else:
        original_df, sheet_label = load_excel(uploaded)
except Exception as exc:
    st.error(f"Could not read this file: {exc}")
    st.stop()

if original_df.empty and len(original_df.columns) == 0:
    st.error("The uploaded file appears to be empty.")
    st.stop()

original_df = original_df.copy()
st.success(f"Loaded **{uploaded.name}** successfully.")
if sheet_label:
    st.caption(f"Worksheet: {sheet_label}")

rows, cols = original_df.shape
missing_total = int(original_df.isna().sum().sum())
duplicate_total = int(original_df.duplicated().sum())
blank_text_total = 0
for col in original_df.select_dtypes(include=["object", "string"]).columns:
    blank_text_total += int(original_df[col].astype("string").str.strip().eq("").fillna(False).sum())

m1, m2, m3, m4 = st.columns(4)
m1.metric("Rows", f"{rows:,}")
m2.metric("Columns", f"{cols:,}")
m3.metric("Missing cells", f"{missing_total:,}")
m4.metric("Duplicate rows", f"{duplicate_total:,}")

tab_preview, tab_quality, tab_clean = st.tabs(["📄 Data preview", "🔎 Data quality", "🧽 Clean & export"])

with tab_preview:
    st.subheader("Uploaded data")
    st.dataframe(original_df.head(500), use_container_width=True, height=420)
    st.caption(f"Showing up to 500 of {rows:,} rows.")
    with st.expander("Column information"):
        info = pd.DataFrame({
            "Column": original_df.columns.astype(str),
            "Data type": [str(x) for x in original_df.dtypes],
            "Non-empty values": [int(original_df[c].notna().sum()) for c in original_df.columns],
            "Missing values": [int(original_df[c].isna().sum()) for c in original_df.columns],
        })
        st.dataframe(info, use_container_width=True, hide_index=True)

with tab_quality:
    st.subheader("Data quality report")
    quality = pd.DataFrame({
        "Column": original_df.columns.astype(str),
        "Data type": [str(x) for x in original_df.dtypes],
        "Missing": [int(original_df[c].isna().sum()) for c in original_df.columns],
        "Missing %": [round(float(original_df[c].isna().mean() * 100), 2) for c in original_df.columns],
        "Unique values": [int(original_df[c].nunique(dropna=True)) for c in original_df.columns],
    })
    st.dataframe(quality, use_container_width=True, hide_index=True)
    text_cols = original_df.select_dtypes(include=["object", "string"]).columns
    whitespace_report = []
    for col in text_cols:
        count = int(original_df[col].astype("string").str.len().gt(
            original_df[col].astype("string").str.strip().str.len()
        ).fillna(False).sum())
        if count:
            whitespace_report.append({"Column": str(col), "Values with extra spaces": count})
    if whitespace_report:
        st.warning("Some text cells contain leading or trailing spaces.")
        st.dataframe(pd.DataFrame(whitespace_report), use_container_width=True, hide_index=True)
    else:
        st.success("No leading or trailing spaces detected in text columns.")
    if duplicate_total:
        st.warning(f"{duplicate_total:,} duplicate rows detected.")
    else:
        st.success("No duplicate rows detected.")

with tab_clean:
    st.subheader("Choose cleaning operations")
    st.write("The original upload remains unchanged. These options are applied to a separate working copy.")
    remove_duplicates = st.checkbox("Remove duplicate rows", value=True)
    trim_spaces = st.checkbox("Trim leading and trailing spaces in text cells", value=True)
    standardize_columns = st.checkbox("Standardize column names (lowercase_with_underscores)", value=False)
    drop_empty_rows = st.checkbox("Remove rows that are completely empty", value=True)

    missing_action = st.selectbox(
        "How should missing values be handled?",
        ["Keep missing values", "Remove rows with any missing value", "Fill text blanks with 'Not provided'"],
    )

    if st.button("Apply cleaning", type="primary", use_container_width=True):
        cleaned = original_df.copy()
        if trim_spaces:
            for col in cleaned.select_dtypes(include=["object", "string"]).columns:
                cleaned[col] = cleaned[col].map(lambda x: x.strip() if isinstance(x, str) else x)
        if standardize_columns:
            new_names = [clean_column_name(c) for c in cleaned.columns]
            # Keep names unique if standardization creates collisions.
            seen = {}
            unique_names = []
            for name in new_names:
                seen[name] = seen.get(name, 0) + 1
                unique_names.append(name if seen[name] == 1 else f"{name}_{seen[name]}")
            cleaned.columns = unique_names
        if drop_empty_rows:
            cleaned = cleaned.dropna(how="all")
        if remove_duplicates:
            cleaned = cleaned.drop_duplicates()
        if missing_action == "Remove rows with any missing value":
            cleaned = cleaned.dropna()
        elif missing_action == "Fill text blanks with 'Not provided'":
            for col in cleaned.select_dtypes(include=["object", "string"]).columns:
                cleaned[col] = cleaned[col].fillna("Not provided")
        st.session_state["cleaned_data"] = cleaned
        st.session_state["cleaned_filename"] = uploaded.name

    if "cleaned_data" in st.session_state and st.session_state.get("cleaned_filename") == uploaded.name:
        cleaned = st.session_state["cleaned_data"]
        st.divider()
        st.subheader("Cleaning result")
        before_rows, before_cols = original_df.shape
        after_rows, after_cols = cleaned.shape
        r1, r2, r3 = st.columns(3)
        r1.metric("Rows after cleaning", f"{after_rows:,}", delta=f"{after_rows - before_rows:+,}")
        r2.metric("Remaining missing cells", f"{int(cleaned.isna().sum().sum()):,}")
        r3.metric("Remaining duplicate rows", f"{int(cleaned.duplicated().sum()):,}")
        st.dataframe(cleaned.head(500), use_container_width=True, height=360)
        csv_bytes = cleaned.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ Download cleaned CSV",
            data=csv_bytes,
            file_name=f"{uploaded.name.rsplit('.', 1)[0]}_cleaned.csv",
            mime="text/csv",
            use_container_width=True,
        )
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            cleaned.to_excel(writer, index=False, sheet_name="Cleaned data")
        st.download_button(
            "⬇️ Download cleaned Excel",
            data=excel_buffer.getvalue(),
            file_name=f"{uploaded.name.rsplit('.', 1)[0]}_cleaned.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    else:
        st.caption("Choose your options and click Apply cleaning to generate the cleaned dataset.")

st.divider()
st.caption("Data Cleaning Studio · Built as an independent portfolio demonstration.")
