import streamlit as st
import pandas as pd
import re
from datetime import datetime

st.set_page_config(page_title="Patent Active/Inactive Processor", layout="wide")

st.title("📊 Patent Active / Inactive Status Processor")

# -----------------------------
# 1. Upload input file
# -----------------------------
uploaded_file = st.file_uploader(
    "Upload input Excel file",
    type=["xlsx", "xls"]
)

if not uploaded_file:
    st.stop()

df = pd.read_excel(uploaded_file)

st.success("Input file loaded successfully")
st.write("Rows:", len(df))

# -----------------------------
# 2. Date input
# -----------------------------
current_date = st.date_input(
    "📅 Select current date",
    value=datetime.today()
)

current_date = pd.to_datetime(current_date)
current_year = current_date.year
last_year = current_year - 1

st.write("Current year:", current_year)
st.write("Last year:", last_year)

# -----------------------------
# 3. Initialize output columns
# -----------------------------
df["Calculated Date"] = pd.NaT
df["Active/Inactive"] = ""
df["Comments"] = ""
df["Validation"] = ""

# -----------------------------
# Rule 1: EP - B
# -----------------------------
ep_mask = (df["Publication Country"] == "EP") & df["Publication Kind Code"].str.startswith("B", na=False)
df.loc[ep_mask, "Calculated Date"] = pd.to_datetime(df["Publication Date"], dayfirst=True, errors="coerce") + pd.DateOffset(months=3)
df.loc[ep_mask & (df["Calculated Date"] < current_date), ["Active/Inactive", "Comments"]] = ["Inactive", "EP-B pub > 3 months"]
df.loc[ep_mask & (df["Calculated Date"] >= current_date), ["Active/Inactive", "Comments"]] = ["Active", "EP-B pub < 3 months"]

# -----------------------------
# Rule 2: WO
# -----------------------------
wo_mask = df["Publication Country"] == "WO"
df.loc[wo_mask, "Calculated Date"] = pd.to_datetime(df["Priority Date"], dayfirst=True, errors="coerce") + pd.DateOffset(months=36)
df.loc[wo_mask & (df["Calculated Date"] < current_date), ["Active/Inactive", "Comments"]] = ["Inactive", "WO prd > 36 months"]
df.loc[wo_mask & (df["Calculated Date"] >= current_date), ["Active/Inactive", "Comments"]] = ["Active", "WO prd < 36 months"]

# -----------------------------
# Rule 3: Design
# -----------------------------
design_mask = df["IP Type"].str.contains("Design", case=False, na=False)
df.loc[design_mask, "Active/Inactive"] = df.loc[design_mask, "Patent Status (Active/Inactive)"]
df.loc[design_mask, "Comments"] = "PCS Design Status"
df.loc[design_mask, "Calculated Date"] = df.loc[design_mask, "Expected Expiry Date"]

# -----------------------------
# Rule 4: Utility Models
# -----------------------------
utility_mask = df["Publication Kind Code"].str.startswith(("U", "Y"), na=False)
df.loc[utility_mask, "Active/Inactive"] = df.loc[utility_mask, "Patent Status (Active/Inactive)"]
df.loc[utility_mask, "Comments"] = "PCS Utility Status"
df.loc[utility_mask, "Calculated Date"] = df.loc[utility_mask, "Expected Expiry Date"]

# -----------------------------
# Rule 5: US cases
# -----------------------------
us_mask = (df["Publication Country"] == "US") & (~design_mask)
df.loc[us_mask, "Calculated Date"] = pd.to_datetime(df["Application Date"], errors="coerce") + pd.DateOffset(years=20)

inactive_ifi_keywords_us = ["Abandoned", "Expired - Lifetime", "Expired - Fee Related"]
active_pcs_mask = df["Patent Status (Active/Inactive)"].str.contains("Active", case=False, na=False)

for kw in inactive_ifi_keywords_us:
    mask = us_mask & active_pcs_mask & df["statusbyifi"].fillna("").str.contains(re.escape(kw), case=False)
    df.loc[mask, ["Active/Inactive", "Comments"]] = ["Inactive", f"PCS US Active, but IFI shows: {kw}"]

active_us_mask = us_mask & active_pcs_mask & (df["Active/Inactive"] != "Inactive")
df.loc[active_us_mask, ["Active/Inactive", "Comments"]] = ["Active", "PCS US Active"]

inactive_us_mask = us_mask & df["Patent Status (Active/Inactive)"].str.contains("Inactive", case=False, na=False)
df.loc[inactive_us_mask, ["Active/Inactive", "Comments"]] = ["Inactive", "PCS US InActive"]

# -----------------------------
# Rule 6: Legal status keywords override
# -----------------------------
inactive_keywords = [
    "Abandon","Cancel","Ceased","Dead","Expired","Lapsed","Withdrawn","Refused",
    "APPLICATION WITHDRAWN","APPLICATION REFUSED","Revoked","Nullification"
]

active_exceptions = [
    "APPLICATION NOT WITHDRAWN",
    "REVOCATION NOT PROCEEDED WITH",
    "ERROR OR CORRECTION"
]

for kw in inactive_keywords:
    mask = df["latest legal event"].str.contains(kw, case=False, na=False)
    df.loc[mask, ["Active/Inactive", "Comments"]] = ["Inactive", f"Legal Status: {kw}"]

for exc in active_exceptions:
    mask = df["latest legal event"].str.contains(exc, case=False, na=False)
    df.loc[mask, ["Active/Inactive", "Comments"]] = ["Active", f"Legal Status: {exc}"]

# -----------------------------
# Rule 7 & 12: Application + 20 years
# -----------------------------
mask_left = df["Active/Inactive"] == ""
df.loc[mask_left, "Calculated Date"] = pd.to_datetime(df["Application Date"], errors="coerce") + pd.DateOffset(years=20)

df.loc[
    mask_left & (df["Calculated Date"] < current_date),
    ["Active/Inactive", "Comments"]
] = ["Inactive", "App date > 20yrs"]

df.loc[
    mask_left & (df["Calculated Date"] >= current_date),
    ["Active/Inactive", "Comments"]
] = ["Active", "App date < 20yrs & no relevant legal status"]

# -----------------------------
# Rule 13: Validation inactive
# -----------------------------
inactive_mask = df["Active/Inactive"] == "Inactive"

event_dates = pd.to_datetime(
    df["latest legal event"].str.extract(r"(\d{8})")[0],
    format="%Y%m%d",
    errors="coerce"
)

event_years = event_dates.dt.year

validation_keywords = ["E701", "GRANT", "Decision of Registration"]

for kw in validation_keywords:
    mask = (
        inactive_mask &
        df["latest legal event"].str.contains(kw, case=False, na=False) &
        event_years.isin([current_year, last_year])
    )
    df.loc[mask, "Validation"] += f" | ⚠️ Check: keyword '{kw}' in recent years"

# -----------------------------
# Rule 14: Active IFI contradiction
# -----------------------------
active_mask = df["Active/Inactive"].str.lower() == "active"
ifi_keywords = ["Abandoned", "Expired - Lifetime", "Expired - Fee Related", "Ceased", "Withdrawn"]

for kw in ifi_keywords:
    pattern = rf"(?:^|\|){re.escape(kw)}(?:\||$)"
    mask = active_mask & df["statusbyifi"].fillna("").str.contains(pattern, case=False, regex=True)
    df.loc[mask, "Validation"] += f" | ⚠️ Check: {kw} in IFI Status"

# -----------------------------
# Download
# -----------------------------
st.subheader("⬇️ Download Output")

output = df.to_excel(index=False, engine="openpyxl")

st.download_button(
    label="Download processed Excel",
    data=output,
    file_name="patent_active_inactive_output.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
