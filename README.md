# Patent Active / Inactive Status Processor (Streamlit)

This application determines **Active / Inactive patent status** based on a fixed sequence of rule-based logic using bibliographic data, legal events, and PCS/IFI status signals.

The tool is built with **Streamlit** and **Pandas** and processes Excel files end-to-end in memory.

---

## What this app does

Given an input Excel file containing patent metadata, the app:

- Applies **country-specific and document-type-specific rules**
- Computes a **Calculated Date** where applicable
- Assigns **Active / Inactive** status
- Adds **Comments** explaining the applied rule
- Flags **Validation warnings** where tagging may be ambiguous or contradictory

The final result is a downloadable Excel file.

---

## High-level rule coverage

The logic includes (non-exhaustive):

- EP B-publications → Publication date + 3 months
- WO publications → Priority date + 36 months
- Design and Utility models → PCS status driven
- US cases → PCS status with IFI override
- Legal status keyword overrides (abandoned, expired, withdrawn, etc.)
- Application date + 20 years fallback
- Final rejection handling (1-year window)
- Country-specific legal event codes (JP, KR, AR)
- Validation checks for recent grants on inactive cases
- Validation checks for IFI contradictions on active cases

**Rule order matters and is intentionally preserved.**

---

## Input requirements

The input Excel file must contain the following columns (case-sensitive):

- Publication Country
- Publication Kind Code
- Publication Date
- Priority Date
- Application Date
- IP Type
- Expected Expiry Date
- Patent Status (Active/Inactive)
- latest legal event
- statusbyifi

If any required column is missing, results may be incorrect.

---

## Output columns added

The app adds or updates these columns:

- `Calculated Date`
- `Active/Inactive`
- `Comments`
- `Validation`

No existing input columns are deleted or renamed.

---

## How to run locally

### 1. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
