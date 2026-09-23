# GMC Quote Automation System — Master Guidebook & Rebuild Specification

**Purpose of this document:** This is the single source of truth for rebuilding the Group Mediclaim (GMC) Quote Preparation Automation System from scratch, with full clarity, no ambiguity, and no bugs. It consolidates every rule, field, default, dropdown, and behavior that must be implemented. Use this document together with the reference UI screenshots of the original project to reconstruct the exact look, structure, and logic.

---

## 1. Project Overview

### 1.1 What the System Does
An AI-assisted automation system that:
1. Accepts **Input Packs** from a client/broker — RFQ/RFP Proposal files and Demography data files — in mixed formats (Excel, PDF, Image, Email, Word).
2. Extracts relevant data using deterministic rule-based logic first, with AI (Azure OpenAI) as a **fallback only** for cases the rule-based logic cannot resolve.
3. Maps every extracted value to a **fixed, pre-defined GMC Quote form field** (dropdown, numeric, date, or remark) — this is a **Fixed-Form Field-Driven Automation System**, not a free-form extractor. The AI must never invent fields or values outside the defined schema.
4. Displays results as structured web tables and produces two downloadable Excel outputs:
   - A **Quote Sheet** (ready to fill into the GMC Quotation system).
   - A **Standardized Demography Sheet** (ready to upload).

### 1.2 Core Design Principle: "Fixed-Form Field-Driven"
- Every possible output field is known in advance (defined in master files).
- Extraction never creates new fields on the fly.
- If extracted data doesn't match a known dropdown value, it is still captured but flagged (see §10 — Unmatched Value Handling), and the field falls back to its default.
- AI is a controlled assistant, not an autonomous decision-maker (see §14 — AI Integration Rules).

---

## 2. System Architecture / File Structure

Rebuild using this exact structure (typos from the original brief are corrected below — use the corrected names):

```
project-root/
├── backend/
│   ├── agents/
│   │   ├── demography_agent.py          # Extracts & builds demography table
│   │   ├── file_classifier_agent.py     # Detects file type/format & routes it
│   │   ├── quote_extraction_agent.py    # Extracts RFQ/RFP quote field data
│   │   └── quote_generation_agent.py    # Assembles final structured quote output
│   ├── core/
│   │   ├── ai_extractor.py              # AI fallback extraction wrapper
│   │   ├── azure_openai_client.py       # Azure OpenAI client (env-driven init)
│   │   ├── demography_engine.py         # Age calculation, column mapping, SME flag
│   │   ├── excel_export.py              # Builds downloadable Excel outputs
│   │   ├── extraction_engine.py         # Core rule-based extraction logic
│   │   ├── file_reader.py               # Unified reader for xlsx/pdf/docx/image/email
│   │   ├── password_handler.py          # Detects & unlocks password-protected files
│   │   ├── sheet_detector.py            # Detects correct sheet/table in multi-sheet files
│   │   └── text_utils.py                # Synonym normalization, fuzzy matching, text cleanup
│   ├── masters/
│   │   ├── dropdown_masters.py          # All dropdown option lists (single source of truth)
│   │   ├── field_master.py              # Canonical field list + header synonym map
│   │   ├── procedure_master.py          # Procedure-wise sublimit → Option 1–4 mapping
│   │   └── zone_master.py               # Zone A/B/C/D city mapping
│   ├── models/
│   │   └── schemas.py                   # Pydantic schemas for all table rows/responses
│   ├── orchestration/
│   │   └── orchestrator.py              # Coordinates agents end-to-end per request
│   ├── tests/
│   │   └── test_hardening_smoke.py      # Smoke tests for edge cases
│   ├── config.py                        # Loads .env, exposes settings object
│   ├── logging.py                       # Central logging config
│   └── main.py                          # FastAPI/Flask app entrypoint & routes
├── frontend/
│   ├── app.js                           # UI logic, API calls, table rendering, switches
│   ├── index.html                       # Page layout
│   └── style.css                        # Styling incl. sticky-header scroll tables
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
└── run.py                               # Single command to launch backend + serve frontend
```

**Note on `models.py` vs `models/schemas.py`:** The original brief nested `schemas.py` under a file called `models.py`, which is not valid (a file cannot contain another file). Corrected structure: `models/` is a package folder containing `schemas.py`.

**Note on `password_handler.py`:** Added explicitly as its own module under `core/` since password-protected file handling is a distinct, non-trivial responsibility (see §5).

---

## 3. Input Handling Rules

1. **Accepted formats:** Excel (.xlsx/.xls), PDF, Image (scanned/photographed documents — OCR required), Email (.msg/.eml or pasted email body), Word (.docx).
2. **Two input categories per case:**
   - RFQ/RFP Proposal file(s) — contains quote terms.
   - Demography data file(s) — contains member-level data.
3. **Multi-file support:** The system must accept **multiple files at once** (e.g., 2 RFQ files + 1 demography file) in a single processing batch, and merge/reconcile extracted data across all of them.
4. **`file_classifier_agent.py`** determines, per uploaded file:
   - File format (drives which reader in `file_reader.py` is used).
   - Content type (RFQ/Proposal vs Demography) — via header/keyword detection, not filename assumptions.
   - Whether the file is password-protected (see §5).

---

## 4. Password-Protected File Handling

**Required behavior:**
1. On upload, `password_handler.py` performs a lightweight check on each file to detect if it is password-protected (attempt to open; catch the specific "protected/encrypted" exception per file type — e.g., `msoffcrypto-tool` for Office files, `pikepdf`/`PyPDF2` for PDFs).
2. Detection happens **before** the user clicks "Process" — files are flagged in the UI (e.g., a lock icon next to the filename).
3. When the user clicks **Process**:
   - If one or more files are flagged as locked, a **password modal/pop-up appears per locked file** (sequential, one at a time, showing the filename), mimicking the native "Enter password" prompt the file would normally show.
   - The user enters the password in this in-app modal.
   - Backend attempts to decrypt/unlock the file in-memory using the supplied password (never persisting the plaintext password).
   - **On success:** the now-unlocked file content is handed to `file_reader.py` for normal extraction, and processing continues automatically.
   - **On failure (wrong password):** show an inline error on the modal ("Incorrect password, try again") and re-prompt for the same file — do not proceed to the next file or fail the whole batch.
4. If a file is not password-protected, no modal appears for it; it proceeds straight to extraction.
5. Passwords are used only transiently in memory for that request and are never logged or stored.

---

## 5. Policy Proposal Date Mode (Age Calculation Switch)

**UI Element:** A toggle switch with two states:
- **OFF (default/left position): "Current Date"**
- **ON (right position): "Use Policy Proposal Start Date"**

**Logic:**

| Switch State | Age Calculated As |
|---|---|
| OFF (default) | `Age = (Current System Date) − (Date of Birth)`, applied to every row in the Demography Table |
| ON | User selects/enters a **Policy Proposal Date**; `Age = (Policy Proposal Date) − (Date of Birth)`, applied to every row |

- If the switch is ON but no Policy Proposal Date has been entered yet, block processing (or fall back to current date) with a clear inline validation message — do not silently calculate with a null date.
- Age must always be a **whole number in completed years** (standard actuarial age-nearest-birthday or age-last-birthday convention — pick one and apply consistently; recommend **age last birthday**, i.e., floor of the exact age in years).
- This recalculation must re-run automatically and update the Age column immediately if the user flips the switch or changes the Policy Proposal Date **after** initial extraction — it should not require re-uploading files.

---

## 6. Demography Extraction — Table Schema

**Fixed 7-column output** (note: brief said "6 columns" but then listed 7 — the correct, final count is **7**):

| Column | Field Name |
|---|---|
| A | Age |
| B | Date of Birth |
| C | Sum Insured |
| D | Relationship |
| E | Name |
| F | EmpCode |
| G | Gender |

### 6.1 Header Synonym Mapping (`field_master.py`)
The extraction must recognize variant column headers in source files and map them to the canonical column. Maintain an extensible synonym dictionary, e.g.:

- **Age** ← "Emp Age", "Employee Age", "AGE", "Member Age"
- **Date of Birth** ← "EMP DOB", "Dependent DOB", "DOB", "D.O.B", "Date of Birth", "Birth Date"
- **Sum Insured** ← "SI", "Sum Insured", "SI Opted", "Coverage Amount"
- **Relationship** ← "Relation", "Relationship with Employee", "Relation with Employee"
- **Name** ← "Employee Name", "Member Name", "Full Name", "Dependent Name"
- **EmpCode** ← "Employee Code", "Emp ID", "Employee ID", "Staff ID"
- **Gender** ← "Sex", "Gender"

This dictionary must be **easily extendable** (single config list, not hardcoded scattered in logic) so new synonyms can be added without touching extraction code.

### 6.2 Age Column Rule
- If Date of Birth is present, **always (re)calculate** Age per §5's rule — do not simply trust an "Age" column from the source file if DOB is available, since DOB + policy date is the authoritative source. If only Age is given (no DOB), retain the given Age and flag DOB as "Not Available."

---

## 7. Connection Between Demography Table and Quote Form Table

Three Quote Form fields (under "Demography Details," §8.3) are **derived from the Demography Table**, not extracted independently from the RFQ file:

| Quote Form Field | Derivation |
|---|---|
| Group Size | Total row count in Demography Table (all lives — employees + dependents) |
| Number of Primary Members | Count of Demography rows where Relationship = "Self"/"Employee" (primary member only, excluding dependents) |
| Flagging SME | **IF** Number of Primary Members **> 250** → `"NO"`. **IF** Number of Primary Members **≤ 250** → `"YES"`. |

> Clarification on the boundary: the brief said "more than 250 → NO" and "less than 250 → YES" without stating what happens at exactly 250. Rule implemented above treats exactly 250 as YES (≤ 250). This must remain a single named constant (`SME_THRESHOLD = 250`) in `dropdown_masters.py` or `field_master.py` so it can be adjusted in one place if the business rule is clarified later.

This link must be **live**: if the Demography Table changes (edited, re-processed, or a new file added), Group Size / Primary Members / SME Flag must recompute automatically.

---

## 8. Quote Form Table — Full Field Specification

All fields render in a table with **4 columns**: `Quote Fields | Coverage Details | Proposed Details | Source Status` (see §12 for column extraction rules and §13 for Source Status logic). Fields are grouped into collapsible/visually distinct sub-sections in this exact order:

### 8.1 Quotation Details
Sum Insured · Policy Tenure · Group Category · Type of Proposal · Brokerage% · Premium Payer · Beneficiary · Plan · Rater Type · Zone · Policy Type · Claim Servicing · TPA

### 8.2 Group Policy Holder Details
Organization Name · PIN Code · State · District · Client Industry Type

### 8.3 Demography Details
Group Size · Number of Primary Members · Flagging SME *(all three derived — see §7)*

### 8.4 Medical Expenses Insurance Coverages
Pre-Existing & Specified Disease · Initial Waiting Period · Room Rent · Room Rent for Normal Room · Room Rent for ICU & Specialty Rooms · Road Ambulance · Air Ambulance · Pre Hospitalization · Post Hospitalization · Medical Advancement Surgery · Maternity Expenses/Benefits · Number of Deliveries/Kids Covered · Maternity Limit – Normal Delivery · Maternity Limit – C Section Delivery · Maternity Waiting Period · AYUSH Treatment · Co-Payment Type · Policy Co-Payment Factor · Procedure-wise Sub Limit/Disease-wise Sublimits/Sub Limit & Disease Wise Capping · Waiver of Cataract Sublimit · Cataract · Cover Not Available (Quote will be referred to the Underwriter)

---

## 9. Hospitalization & Treatment Details Table — Full Field Specification

Same 4-column format as §8, grouped into sub-sections:

### 9.1 Modern Treatments
Uterine Artery Embolization and HIFU · Balloon Sinuplasty · Deep Brain Stimulation · Oral Chemotherapy · Immunotherapy (incl. Monoclonal Antibody Injection) · Intravitreal Injections (Except Lucentis) · Intravitreal Injections · Robotic Surgeries · Vaporisation of the Prostate (Green/Holmium Laser) · Bronchial Thermoplasty · Stereotactic Radiosurgery · Intraoperative Neuro Monitoring · Stem Cell Therapy/Stem Cell Treatment Coverage · Gamma Knife/CyberKnife Surgery · Remicade/Avastin Injection · Biodegradable Stent · Cochlear Implant Treatment · Lucentis · Functional Endoscopic Sinus Surgery · Ayurvedic Treatment

### 9.2 Medical Coverage
Day Care Expenses/Day Care Procedures/Day Care Treatment · Domiciliary Hospitalization · Dental Treatment/Accident Dental Treatment · LASIK Surgery/LASIK Treatment · Refractive Error Correction · Psychiatric Ailments/Psychiatric Treatment · Organ Donor/Organ Donor Expenses · Covid-19 Treatment · Hospitalization following Terrorism · Internal Congenital Diseases · External Congenital Diseases

### 9.3 Maternity & Newborn
Baby One Day Cover/Newborn Baby Coverage · Newborn Baby Cover from Day One within Family Floater SI · Maternity Complication · Pre and Post Natal Treatment up to Maternity Limit · Twin Delivery

### 9.4 Hospital Expenses
Anesthesia Charges · Charges of Surgeon's Own Instruments used in Surgeries · Assistant Surgeon/Assistant Doctor/Assistant Consultant/Attendant Charges · Nursing Allowance · Hospital Cash Benefit

### 9.5 Health & Wellness
Wellness Programmes/Offerings · Health Check-Up · Master Health Check-Up for Employees (Inbuilt Cover) · Health Card Type

### 9.6 Policy Conditions
Claim Submission and Intimation Clause · Proportionate Clause · Portability · Terrorism/Terrorism and Epidemic Outbreak · Correction Endorsements · Special Clause/Coverage

---

## 10. Term Equivalence / Synonym Handling (Critical Anti-Confusion Rules)

The system must treat the following as **identical in meaning** (normalize to one canonical label before matching/display), via a dedicated normalization function in `text_utils.py`:

| Canonical Term | Recognized Variants |
|---|---|
| Stem Cell Therapy | "Stem Cell Treatment Coverage" |
| Day Care Expenses | "Day Care Procedures", "Day Care Treatment" |
| Newborn Baby Coverage | "Baby Day One Cover", "Baby Day 1 Cover", "Baby Coverage" |
| Dental Treatment | "Accident Dental Treatment" |
| LASIK Surgery | "LASIK Treatment" |
| Hospitalization following Terrorism | "Hospitalization due to Terrorism Effect" |
| Organ Donor | "Organ Donor Expenses" |
| Domiciliary Hospitalization | "Domicillary Hospitalization" (misspelling) |
| Pre and Post Natal Treatment up to Maternity Limit | "Pre and Post Natal Expenses" |
| Not Found / Not Applicable / Not Covered / Waived Off / No Waiting Period | All treated as the same negative/absent-coverage state for matching purposes, though the **originally extracted wording is preserved for display** — only the *matching logic* treats them as equivalent. |

**Critical distinction (must NOT be merged):**
- **"Ayurvedic Treatment"** (a Modern Treatments field) and **"AYUSH Treatment"** (a Medical Expenses Coverage field, referring to a sub-limit amount) are **different fields with different meanings** and must never be cross-mapped or confused with each other.

Build this equivalence map as a structured, testable lookup table (e.g., a dict of canonical → [variants]) — not scattered `if/elif` string checks — so it is easy to extend and unit-test.

---

## 11. Default Values (Applied Only When Field Is Empty in Input)

| Field | Default Value | Condition |
|---|---|---|
| Policy Tenure | 1 Year | Always default (only option) |
| Group Category | Employer-Employee | If empty |
| Type of Proposal | **New Business** | If empty in input file |
| Type of Proposal | **Own Renewal** | If proposing/incumbent company name = "Bajaj" |
| Type of Proposal | **Roll Over** | If proposing/incumbent company name ≠ "Bajaj" (i.e., business is moving from a non-Bajaj insurer) |
| Premium Payer | GroupManager | If empty |
| Beneficiary | Employee/Nominee | If empty |
| Plan | Individual | If empty |
| Zone | Pan India | If empty |
| Policy Type | Base IPD | If empty |
| Claim Servicing | In House | If empty |
| TPA | In House Administration Team | Only if Claim Servicing = "In House" (default or extracted) |
| Client Industry Type | Others | If empty |

**Fields requiring manual RM input (never auto-filled):**
- Brokerage % → always left blank/editable for the Relationship Manager to fill in.

**Fields always set to a fixed placeholder:**
- Rater Type → always `-` (this field is not extracted or defaulted; it is simply not used at quoting stage).

---

## 12. Dropdown Master Lists (`dropdown_masters.py`)

All dropdown-bound fields validate extracted values against these exact lists. This is the **single source of truth** — the frontend dropdowns and backend validation must both read from this one master file (never duplicate the list in two places).

| Field | Dropdown Options |
|---|---|
| Policy Tenure | 1 Year |
| Group Category | Employer-Employee, Non-Employer-Employee |
| Type of Proposal | New Business, Roll Over, Own Renewal |
| Premium Payer | Insured, GroupManager |
| Beneficiary | Employee/Nominee |
| Plan | Individual, Floater |
| Zone | Zone A, Zone B, Zone C, Zone D, Pan India |
| Policy Type | Base IPD, Base OPD/Structured OPD/HPR, Corporate Buffer, Critical Illness, Dependent Only, Parental IPD, Parental Top Up/Super Top IPD, Wellness |
| Claim Servicing | In House, TPA |
| Client Industry Type | IT and ITES, Manufacturing, Aviation, Media and Entertainment, Pharmaceuticals, Real Estate, Hospitality, Healthcare and Hospitals, Education and Training, Insurance, Bank, NBFC, Other Financial Institution, NGO/Trust, Association, Society, SHG, Club, Military/Para Military Force, Police Force, Law Enforcement Agencies, Political Party/Firms, Grocery/Kirana Stores, Gymkhanas, Religious Group, Any Kind of Shops, Event Management Companies/Teams, Mining Industry, Sea-Voyage Carriers, Film Industry, Adventure Sport Organizations, Tourism Industry, Agriculture Industry, Logistics and Transportation, Others |
| Pre-Existing & Specified Disease | Covered, Waived Off, Applicable, Not Covered, Not Found, Not Applicable |
| Initial Waiting Period | Covered, Waived Off, Applicable, Not Covered, Not Found, Not Applicable, 15 Days, 30 Days |
| Room Rent | Not Applicable, Rent up to Single Private Room, Rent up to Twin Sharing, Rent in General Ward, 0.5% of SI max up to 2500, 1% of SI max up to 5000, 1.5% of SI max up to 7000, 2% of SI max up to 7500 |
| Pre Hospitalization | 0, 15, 30, 60, 90, 120 |
| Post Hospitalization | 0, 30, 60, 90, 120, 180 |
| Medical Advancement Surgery | Upto 25% SI, Upto 50% SI, Upto SI |
| Maternity Expenses/Benefits | Covered, Waived Off, Not Covered, Not Found, Not Applicable |
| Number of Deliveries/Kids Covered | 1, 2, 3 |
| Maternity Limit – Normal Delivery | 50000 |
| Maternity Limit – C Section Delivery | 50000 |
| Maternity Waiting Period | 9 Months Waiting Period, No Waiting Period, Covered, Waived Off, Applicable, Not Covered, Not Found, Not Applicable |
| AYUSH Treatment | 25000 |
| Co-Payment Type | All Claims, Non-Network Hospitals/Clinics, Not Applicable |
| Policy Co-Payment Factor | 5% Copay, 10% Copay, 15% Copay, 20% Copay, 25% Copay, 30% Copay |
| Waiver of Cataract Sublimit | Covered, Waived Off, Applicable, Not Covered, Not Found, Not Applicable |

> **Note on single-value dropdowns** (Policy Tenure, Maternity Limits, AYUSH Treatment): these are effectively fixed constants rather than real "choices." Implement them the same way structurally (so the UI is consistent) but treat any conflicting extracted value as a mismatch to flag (§14), not silently overwrite.

### 12.1 Zone Master (`zone_master.py`)
| Zone | Cities/Regions |
|---|---|
| Zone A | Ahmedabad, Kolkata (incl. Howrah, North 24 Parganas), Hyderabad, Secunderabad, Vadodara, Surat, Delhi/NCR, Mumbai (incl. Navi Mumbai, Thane, Kalyan) |
| Zone B | Rest of India — excluding cities mapped to Zone A, Zone C, Zone D |
| Zone C | Goa, Uttarakhand, Tamil Nadu, Sikkim, Chandigarh, Chhattisgarh, Punjab, Andhra Pradesh |
| Zone D | Andaman & Nicobar Islands, Bihar, Lakshadweep, Tripura, Manipur, Jammu & Kashmir, Mizoram, Odisha, Himachal Pradesh, Arunachal Pradesh, Meghalaya, Jharkhand, Nagaland |
| Pan India | Default when city/location doesn't resolve to a single zone, or is explicitly stated as Pan India |

Zone lookup logic: if the input file mentions a specific city/state, resolve it to a Zone via this table; if no location is given or it spans multiple zones, use "Pan India" (default per §11).

### 12.2 Plan vs. Policy Type Overlap
Many source files put Policy Type information inside a field literally labeled "Plan." The extraction logic must:
1. Check the "Plan" column/field content against the **Policy Type** dropdown list first.
2. If it matches a Policy Type option, populate **Policy Type** with it (not force it into the Plan field's own dropdown of Individual/Floater).
3. Still separately determine the true "Plan" (Individual/Floater) from its own contextual clues, or apply the default.

---

## 13. Procedure-wise Sub-Limit Mapping (`procedure_master.py`)

For the "Procedure-wise Sub limit / Disease-wise Sublimits / Sub Limit & Disease Wise Capping" field, the source file typically gives a rupee amount per named procedure. Map amount → Option label using this table:

| Procedure | Option 1 | Option 2 | Option 3 | Option 4 |
|---|---|---|---|---|
| Coronary Artery Bypass Grafting (CABG) | 1,50,000 | 1,20,000 | 80,000 | 65,000 |
| Valve Replacement | 1,50,000 | 1,20,000 | 80,000 | 65,000 |
| PTCA (per event hospitalization) | 1,30,000 | 1,00,000 | 70,000 | 50,000 |
| Total Knee Replacement (per event hospitalization) | 1,30,000 | 1,00,000 | 70,000 | 50,000 |
| Total Hip Replacement | 1,50,000 | 1,20,000 | 80,000 | 65,000 |
| Arthroscopic Surgeries | 1,50,000 | 1,20,000 | 80,000 | 65,000 |
| Cholecystectomy | 35,000 | 25,000 | 20,000 | 20,000 |
| Kidney Stone Removal (incl. DJ Stent Removal) | 35,000 | 30,000 | 25,000 | 20,000 |
| Appendectomy | 30,000 | 25,000 | 20,000 | 15,000 |
| Hysterectomy | 35,000 | 25,000 | 20,000 | 15,000 |
| Fistulectomy | 35,000 | 25,000 | 20,000 | 15,000 |
| Septoplasty | 35,000 | 25,000 | 20,000 | 15,000 |
| Hernia Repair | 35,000 | 25,000 | 20,000 | 15,000 |
| Haemorrhoidectomy | 25,000 | 20,000 | 15,000 | 15,000 |
| Tympanoplasty | 25,000 | 20,000 | 15,000 | 15,000 |
| Arthroscopy | 25,000 | 20,000 | 10,000 | 10,000 |
| Cataract (one eye) | 35,000 | 25,000 | 20,000 | 15,000 |
| Tonsillectomy | 20,000 | 15,000 | 10,000 | 10,000 |
| Dialysis (per session) | 5,000 | 4,000 | 2,000 | 2,000 |

**Matching rule:** Normalize the rupee figure (strip commas/₹/spaces) before comparing to the table. If the amount doesn't exactly match any of the 4 options for that procedure, treat it as an unmatched value (§14) — display the raw extracted amount in brackets and flag it, rather than forcing it into the nearest option.

---

## 14. Unmatched Value Handling (Applies Anywhere a Dropdown Exists)

When extracted data does **not** match any option in that field's dropdown master:
1. The **field itself still displays the system default** for that field (per §11 if one exists; otherwise "Not Available").
2. The raw extracted value is preserved and shown as a flagged note directly below/after the relevant table, in the format:
   `Unmatched word "<extracted value>" was detected for <Field Name>`
3. Multiple unmatched values across a table are listed as multiple such comment lines (not merged/overwritten).
4. This behavior applies to **every** dropdown-bound field, not just Policy Type (Policy Type was the brief's example, but the rule is general).

---

## 15. Semantic Field Decomposition Engine (Keyword-to-Field Understanding Logic)

This is the single most important piece of extraction logic in the whole system. It replaces naive "copy the cell value into the field" behavior with genuine **understanding of what the extracted sentence is actually saying**, so that one combined block of source text gets correctly broken apart and routed into every specific Quote Field it actually describes — for **both** the "Coverage Details" source column and the "Proposed Details" source column, independently, for **every** field group in the Quote Form Table (not just Room Rent).

### 15.1 The Core Idea, Stated Plainly

> **A block of extracted text is not one opaque string to dump into one field. It is a set of statements, and each statement belongs to whichever Quote Field(s) its own wording is actually about. The Quote Field names themselves (and their known synonyms/indicator words) are the keywords the engine searches for inside the text in order to decide where each statement belongs.**

This must be implemented as one **generic, reusable engine** — not a one-off `if room_rent:` / `if maternity:` script. The engine is configured per **Field Group** (defined below) and the same decomposition algorithm runs for all of them.

### 15.2 Field Groups

A **Field Group** is a named cluster of one or more related Quote Fields that commonly appear together in a single sentence/paragraph of source text. Define these as structured config (not hardcoded logic) in `field_master.py`:

```python
FIELD_GROUPS = {
    "room_rent": {
        "parent_field": "Room Rent",
        "child_fields": {
            "Room Rent for Normal Room": {
                "keywords": ["normal", "normal room", "for normal"]
            },
            "Room Rent for ICU & Specialty Rooms": {
                "keywords": ["icu", "specialty", "specialty room", "for icu"]
            }
        }
    },
    "hospitalization": {
        "parent_field": None,   # no umbrella field — both children are independent
        "child_fields": {
            "Pre Hospitalization":  {"keywords": ["pre-hosp", "pre hosp", "pre-hospitalization", "pre hospitalization"]},
            "Post Hospitalization": {"keywords": ["post-hosp", "post hosp", "post-hospitalization", "post hospitalization"]}
        }
    },
    "maternity": {
        "parent_field": "Maternity Expenses / Benefits",
        "child_fields": {
            "Number of Deliveries/Kids Covered": {
                "keywords": ["children", "child", "deliveries", "kids covered", "number of deliveries"],
                "expected_type": "dropdown", "dropdown_ref": "Number of Deliveries/Kids Covered"
            },
            "Maternity Limit – Normal Delivery": {
                "keywords": ["normal delivery", "for normal"], "expected_type": "amount"
            },
            "Maternity Limit – C Section Delivery": {
                "keywords": ["c-section", "c section", "cesarean"], "expected_type": "amount"
            },
            "Maternity Waiting Period": {
                "keywords": ["waiting period", "month waiting", "waived"], "expected_type": "dropdown",
                "dropdown_ref": "Maternity Waiting Period"
            }
        }
    },
    "modern_treatments": {
        "parent_field": None,   # flat group — every treatment name IS a field
        "child_fields": {
            # one entry per field in §9.1, keyed by canonical name,
            # "keywords" = the field's own name + all synonyms from §10
            # e.g. "Stem Cell Therapy": {"keywords": ["stem cell therapy", "stem cell transplantation",
            #                                          "stem cell treatment coverage"]}
        }
    }
    # Additional groups follow the same shape for every multi-field cluster in §8/§9.
}
```

Every Quote Field and Hospitalization & Treatment field that is **not** part of any group is treated as its own one-field group (the existing behavior from earlier sections still applies to those — this engine only changes behavior for grouped fields).

### 15.3 The Decomposition Algorithm

Run this once for the **Coverage Details** text and once, independently, for the **Proposed Details** text of a given Field Group (the two source columns are decomposed separately and never mixed — see §18 for how each column's raw text is identified in the first place).

**Step 1 — Capture in full.** Extract the complete, unmodified source text for this Field Group. Never truncate.

**Step 2 — Segment.** Break the text into discrete statement units. A "statement unit" boundary is any of: a bullet marker (•, -, *), a line break, a full stop followed by a capital letter/new clause, a semicolon, or (only within a single clause, not across the whole text) the connector words **"and"** / **"&"** when they join two clearly distinct quantities (e.g., "2% for Normal **and** 4% for ICU" → two units; but "Employee **and** Spouse" inside one clause about eligibility stays one unit — see Step 6 for how to tell these apart).

**Step 3 — Keyword scan per unit.** For each segmented unit, check it against the **active Field Group's own child-field keyword sets only** (never scan against a different group's keywords — the engine already knows which group's text it is looking at because extraction assigned this raw block to this category before decomposition began). A match means: the unit contains the field's canonical name, a listed synonym (§10), or a listed indicator keyword (e.g., "ICU" as a stand-in for "Room Rent for ICU & Specialty Rooms").

**Step 4 — Assign.**
- **Single match** → the full unit's text becomes that child field's value.
- **Multiple fields named together in one unit**, joined by "/" or "or" or "and" in a way that means *the same condition applies to all of them* (e.g., "Cyberknife treatment/Stem Cell Transplantation") → assign the **identical** unit text to **every** matched field. Do not split a shared condition into fragments that lose meaning.
- **No child-field keyword match, but the unit is clearly about the category in general** → assign it to the group's `parent_field` (if one exists). A parent field can receive a unit **in addition to** a child field receiving a different (or even the same) unit — parent and child assignment are not mutually exclusive.
- **No match to any child field or the parent field, and the unit describes something genuinely unrelated to this category** → do not discard it. Carry it forward to the **Additional Details Table** (§16) rather than dropping it silently.

**Step 5 — Type/format validation before final assignment.** Before writing a value into a child field, check the field's `expected_type` (from `field_master.py`, e.g., `"amount"`, `"dropdown"`, `"days"`, `"free_text"`). If the candidate text does **not** plausibly satisfy that type (e.g., the field's dropdown only allows `1`/`2`/`3` but the candidate text is a prose sentence like "no limit on number of deliveries"), do **not** force it into that field. Instead, fall back to assigning it to the group's `parent_field`, since a general statement about the category is exactly what an umbrella field is for. This prevents malformed values from ever reaching a field that can't represent them, and it is why the Maternity "Proposed Details" example below assigns "No Limit on Number of child deliveries" to **Maternity Expenses/Benefits**, not to **Number of Deliveries/Kids Covered** — the sentence doesn't reduce to a clean `1`/`2`/`3` value, so the umbrella field is the correct destination instead.

**Step 6 — Distinguish a real split-boundary "and" from a same-clause "and".** A connector word only creates a new unit when the words on either side of it each independently match a *different* child-field keyword (e.g., "...for Normal **and** 4% for ICU" — "Normal" and "ICU" are different child keywords, so split here). If neither side matches a distinct child keyword (e.g., "covered for Employee and Spouse"), treat it as one unit.

**Step 7 — Shared trailing clauses.** A trailing clause that follows a split point may modify only one branch, or both. Decide using its own wording:
- If the trailing clause itself contains a child-field keyword (e.g., "...Normal Room Rent is inclusive of Nursing Charges" contains "Normal Room"), attach it **only** to that specific child field (plus the parent field, since the parent field's value is always the reassembled full original sentence — see §15.4).
- If the trailing clause contains no specific child-field keyword and reads as a general qualifier, attach it to **every** child field the preceding split produced, plus the parent field.

**Step 8 — Positional/tier heuristic (last resort within a group, before AI fallback).** Some source files present two or more parallel statements for the same field group where **neither statement contains an explicit child-field keyword** — they differ only by a descriptive qualifier in parentheses (e.g., "(Single Pvt AC Room)" vs "(At Actuals)"). For these cases only, maintain an explicit, testable **Tier Indicator Keyword List** in `field_master.py` (e.g., `"at actuals"`, `"no capping"`, `"full reimbursement"` → typically indicate the *uncapped/ICU* tier of a Room-Rent-style field; a named room category with a capped rupee figure → typically indicates the *Normal Room* tier). Apply this list to resolve ambiguous parallel statements **before** invoking AI. If the tier-indicator list also fails to resolve it, only then hand the ambiguous unit set to `ai_extractor.py` per the AI-fallback rules in §20 — never guess silently outside of a documented rule.

### 15.4 The Parent/Umbrella Field's Own Value

Whenever a group has a `parent_field` (e.g., "Room Rent", "Maternity Expenses/Benefits"), that field's displayed value is the **full original, unsplit source text** for that block (Coverage Details and Proposed Details each keep their own full-text version of the parent field). The parent field is never left as a fragment — it always represents "everything the source said about this category," while its child fields represent the specific sub-values pulled out of that same text.

### 15.5 Worked Examples (Reference Behavior — Must Match Exactly)

#### Example A — Modern Treatments (flat group, no parent field)

**Coverage Details (source):**
> "• Oral chemotherapy • Uterine Artery Embolization and HIFU • Balloon Sinuplasty • Deep Brain stimulation • Immunotherapy - Monoclonal Antibody to be given as injection • Intra vitreal injections (Injection Lucentis & Avastin restricted to Rs. 50000 per family) • Bronchial Thermoplasty • Cochlear Implant • Vaporisation of the prostate (Green laser treatment or holmium laser treatment)"

- Each bullet is a segmentation unit (Step 2 — bullet marker `•`).
- Each unit is keyword-matched directly against the flat list of Modern Treatment field names/synonyms (Step 3–4).
- Every treatment **named in this text** → that field = "Covered" (or the specific descriptive detail given, e.g., Intravitreal Injections gets the Rs. 50,000/family detail attached).
- Every Modern Treatment field **from §9.1 that is NOT named anywhere in this text** → remains "Not Found"/Not Applicable for this source column. (This is the general rule stated in the brief: understanding which treatments are explicitly listed tells the engine, by absence, that unlisted treatments in the same family are not applicable per this source.)

**Proposed Details (source):**
> "50% Co-Pay for cyberknife treatment/Stem Cell Transplantation. Cochlaer Implant treatment shall be restricted to 50% of the SI"

- Segment by full stop (Step 2): Unit 1 = "50% Co-Pay for cyberknife treatment/Stem Cell Transplantation"; Unit 2 = "Cochlaer Implant treatment shall be restricted to 50% of the SI" (note "Cochlaer" is a misspelling of "Cochlear" — normalized via §10-style fuzzy/synonym matching before field lookup).
- Unit 1 names two fields joined by "/" with one shared condition (Step 4, shared-condition rule) → identical text assigned to both:

| Field | Value |
|---|---|
| Cyberknife Treatment | 50% Co-Pay for Cyberknife/Stem Cell Transplantation |
| Stem Cell Transplantation | 50% Co-Pay for Cyberknife/Stem Cell Transplantation |
| Cochlear Implant Treatment | Cochlaer Implant treatment shall be restricted to 50% of the SI |

#### Example B — Room Rent (parent + 2 children)

**Coverage Details:**
> "2% of SI for Normal and 4% for ICU. Normal Room Rent is inclusive of Nursing Charges. Rent for Normal Room Up to Single Private Room"

- Split at "and" because "Normal" and "ICU" are distinct child keywords on either side (Step 6): Unit 1 = "2% of SI for Normal", Unit 2 = "4% for ICU".
- Remaining sentences each contain the keyword "Normal Room" → attach only to the Normal Room child (Step 7).

| Field | Value |
|---|---|
| Room Rent (parent) | 2% of SI for Normal and 4% for ICU. Normal Room Rent is inclusive of Nursing Charges. Rent for Normal Room Up to Single Private Room |
| Room Rent for Normal Room | 2% of SI for Normal. Normal Room Rent is inclusive of Nursing Charges. Rent for Normal Room Up to Single Private Room |
| Room Rent for ICU & Specialty Rooms | 4% for ICU |

**Proposed Details:**
> "Daily Room Rent Eligibility - Normal Room: INR 6000 (Single Pvt AC Room)" / "Daily Room Rent Eligibility - Normal Room: INR 12000 (At Actuals)"

- Neither statement's core clause contains an unambiguous ICU keyword — both literally say "Normal Room." This is the **Step 8 tier-heuristic** case: the qualifier "(Single Pvt AC Room)" indicates a capped, named-room tier → Normal Room; the qualifier "(At Actuals)" is on the Tier Indicator Keyword List as an uncapped/ICU-style indicator → ICU & Specialty Rooms.

| Field | Value |
|---|---|
| Room Rent (parent) | Daily Room Rent Eligibility - Normal Room: INR 6000 (Single Pvt AC Room)\nDaily Room Rent Eligibility - Normal Room: INR 12000 (At Actuals) |
| Room Rent for Normal Room | Daily Room Rent Eligibility - Normal Room: INR 6000 (Single Pvt AC Room) |
| Room Rent for ICU & Specialty Rooms | Daily Room Rent Eligibility - Normal Room: INR 12000 (At Actuals) |

#### Example C — Pre/Post Hospitalization (2 independent children, no parent)

**Coverage Details:** "Pre-Hosp Expenses - Upto 30 days" / "Post-Hosp Expenses - Upto 60 Days"
**Proposed Details:** "Pre-Hosp Expenses - Upto 60 days" / "Post-Hosp Expenses - Upto 90 Days"

Each line already contains its own explicit keyword ("Pre-Hosp" / "Post-Hosp") — direct 1-to-1 assignment (Step 4a), numeric value only (matches the field's `expected_type: "days"`):

| Field | Coverage Details | Proposed Details |
|---|---|---|
| Pre Hospitalization | 30 days | 60 days |
| Post Hospitalization | 60 days | 90 days |

#### Example D — Maternity (parent + 4 children, includes the type-validation edge case)

**Coverage Details** (paraphrased multi-bullet block — see original for full wording) contains, among other bullets:
- "Covered For Upto 125430 For Normal & For C-Section Delivery Upto 125340" → splits at "For Normal" / "For C-Section" (Step 6) into the two Maternity Limit fields; the word "Covered" at the start also feeds the parent field.
- "Maternity covered for only first 2 children including still birth" → matches the "children" keyword → Number of Deliveries/Kids Covered.
- "9 Month Waiting Period for Maternity → Covered" → matches "Waiting Period" → Maternity Waiting Period, value preserved as the descriptive phrase "9 Month Waiting Period for Maternity."
- All other bullets (Employee & Spouse eligibility, treatment-by-any-doctor, well-baby/well-mother care, complications-within-FSI, no delivery-history requirement, full-SI-in-life-threatening-situation) match **none** of the four child-field keyword sets → per Step 4's parent-fallback rule, they remain part of the full text assigned to the **parent field**, "Maternity Expenses/Benefits," rather than being discarded.

| Field | Value |
|---|---|
| Maternity Expenses/Benefits (parent) | Covered |
| Number of Deliveries/Kids Covered | Maternity covered for only first 2 children including still birth |
| Maternity Limit – Normal Delivery | Covered For Upto 125430 For Normal |
| Maternity Limit – C Section Delivery | For C-Section Delivery Upto 125340 |
| Maternity Waiting Period | 9 Month Waiting Period for Maternity |

**Proposed Details:** "No Limit on Number of child deliveries"

- This unit's wording matches the "children"/"deliveries" keyword set for **Number of Deliveries/Kids Covered** — but that field's `expected_type` is `dropdown` restricted to `1`/`2`/`3` (§12). The phrase "No Limit" cannot satisfy that type (Step 5) →  it is **not** written into Number of Deliveries/Kids Covered. Instead, since it is a general statement about the richness of the maternity benefit, it is routed to the **parent field**:

| Field | Value |
|---|---|
| Maternity Expenses/Benefits (parent) | No Limit on Number of child deliveries |
| Number of Deliveries/Kids Covered | *(no value from this source — remains whatever Coverage Details produced, or Not Available)* |
| Maternity Limit – Normal Delivery | *(no value from this source)* |
| Maternity Limit – C Section Delivery | *(no value from this source)* |
| Maternity Waiting Period | *(no value from this source)* |

This example is the clearest illustration of **why Step 5 (type validation) exists**: a purely keyword-based match without a type check would have wrongly forced "No Limit on Number of child deliveries" into a field that can only legally hold `1`, `2`, or `3`.

### 15.6 Implementation Notes for the IDE / Codebase

- Implement this as one function, e.g. `decompose_field_group(raw_text: str, group: FieldGroupConfig, source_column: Literal["coverage","proposed"]) -> dict[str, str]`, living in `core/extraction_engine.py`, called once per Field Group per source column.
- `FIELD_GROUPS`, each field's `keywords`, `expected_type`, and the `TIER_INDICATOR_KEYWORDS` list all live in `masters/field_master.py` as data, **not** inline in the engine — so new groups/fields/keywords can be added without touching the algorithm.
- The engine must run **twice per group per RFQ file** — once for the Coverage Details text, once for the Proposed Details text — and the two results are kept as separate columns in the final table (per the 4-column table format in §8), never merged into one value.
- Unclaimed segments that don't belong to any field in the active group, and don't fit the parent field either, must be forwarded to whatever mechanism populates the Additional Details Table (§16) — this decomposition engine should return an explicit `unassigned: list[str]` alongside its field assignments so the orchestrator can route those leftovers correctly.
- Step 8 (tier heuristic) and any case that still fails after Steps 1–8 are exactly the conditions under which `ai_extractor.py` should be invoked (§20) — the AI call should be given the same group config (field names, keywords, expected types) so its answer is validated the same way a rule-based answer would be.
- Unit test each of the four worked examples in §15.5 verbatim in `test_hardening_smoke.py` — they are the acceptance criteria for this engine.

---

## 16. Additional Details Table

- Contains any data/fields found in the input file that **do not correspond** to any field defined in the Quote Form Table (§8) or the Hospitalization & Treatment Details Table (§9).
- Content is **dynamic per case** — different input files will populate different rows here; there is no fixed field list for this table (unlike the other two).
- Uses the **same 4-column format**: `Quote Fields | Coverage Details | Proposed Details | Source Status`.
- Source Status for this table only ever shows **"RFQ Data"** or **"Not Available"** (no "Default Data," since there are no defaults for undefined fields — see §17).

---

## 17. Source Status Logic (All Three Tables)

The 4th column, **Source Status**, communicates where a displayed value came from.

### 17.1 Quote Form Data Table — 3 possible statuses
| Status | Meaning |
|---|---|
| RFQ Data | Value was found in the input RFQ/Proposal file for this field |
| Default Data | Field was empty in input; system applied the coded default (§11) |
| Not Available | Field was empty in input **and** no default exists for it |

### 17.2 Additional Details Table & Hospitalization/Treatment Table — 2 possible statuses
| Status | Meaning |
|---|---|
| RFQ Data | Value was found in the input file |
| Not Available | No value found (these tables have no default-value concept) |

### 17.3 RFQ Data Validity Icon
Whenever Source Status = "RFQ Data" **and** the field is dropdown-bound, show a validity icon next to it:
- ✅ **Green check** — the extracted value matches one of the field's defined dropdown options exactly (after synonym normalization, §10).
- ❌ **Red cross** — the extracted value does not match any dropdown option (this pairs with the "Unmatched word..." note under §14).

Non-dropdown fields (free text/numeric, e.g., Organization Name, PIN Code) never show this icon — only "RFQ Data"/"Default Data"/"Not Available" text applies to them.

---

## 18. Coverage Details vs. Proposed Details Column Extraction Rule

Input RFQ files commonly have their own column headers for values (varying per client). Map source columns to output columns using **keyword detection on the source column header**, not fixed column position:

| Output Column | Populate From Source Column Whose Header Contains... |
|---|---|
| Coverage Details | The keyword **"Policy"** or **"Coverage"** (e.g., "Current Policy Coverage", "Coverage Terms") |
| Proposed Details | The keyword **"Proposed"** (e.g., "Proposed Terms", "Proposed Coverage") |

If a source file has only one data column with neither keyword (single-column RFQ), populate **Coverage Details** with it and leave Proposed Details as "Not Available," since Coverage Details represents the baseline/current terms.

---

## 19. UI/UX Requirements

### 19.1 Policy Proposal Date Mode Switch
- Toggle control, OFF (left/default) = "Current Date," ON (right) = "Use Policy Proposal Start Date."
- When ON, reveal a date picker for the Policy Proposal Date.
- Recalculates Demography Age column live on toggle/date change (§5).

### 19.2 Table Scrolling Behavior (applies to all 3 result tables: Quote Form, Additional Details, Hospitalization & Treatment — and the Demography table)
- Each table renders inside its own scroll container with a **fixed max-height**.
- **Vertical scroll** inside the container for tall tables — the outer page should not need excessive scrolling.
- **Horizontal scroll** inside the container for wide tables.
- **Sticky table header** — column headers (`Quote Fields | Coverage Details | Proposed Details | Source Status`) remain visible while scrolling within the container.
- Long cell text must wrap/truncate gracefully (e.g., `white-space: normal; word-break: break-word;` with a reasonable max cell width) — never overflow and break the row layout.
- Row hover highlighting and readability (alternating row shading, adequate padding) must be preserved.
- This is a **pure CSS/layout concern** — it must not alter or interfere with the existing table-rendering logic or column-to-field mapping.

### 19.3 Sub-Section Grouping
Quote Form Table and Hospitalization & Treatment Table must visually group fields under their named sub-sections (§8.1–8.4, §9.1–9.6) — e.g., a sub-header row or collapsible section label — so the long field lists are scannable rather than one flat list.

### 19.4 File Upload Area
- Supports multi-file selection/drag-drop in one action.
- Shows per-file status: format detected, classified type (RFQ vs Demography), and a lock icon if password-protected.
- "Process" button triggers the password-modal flow (§4) before extraction begins.

### 19.5 Downloads
- Two separate "Download Excel" actions: one for the Quote Sheet, one for the Standardized Demography Sheet — built via `excel_export.py`.

---

## 20. AI Integration Rules (Critical — Controlled Fallback Only)

1. **Setup:** All AI configuration (Azure OpenAI endpoint, key, deployment name, API version) lives in `.env`. Once `.env` is populated and the app is (re)started, `azure_openai_client.py` initializes the client automatically — **no additional manual wiring** should be required by the user. `.env.example` documents every required variable with placeholder values.
2. **AI is fallback-only, never primary.** The default and expected path for every field is the deterministic rule-based logic in `extraction_engine.py` / `demography_engine.py` / `text_utils.py`. AI (`ai_extractor.py`) is invoked **only when** the rule-based logic:
   - Cannot locate a value for a field at all where the source clearly seems to contain one (e.g., ambiguous phrasing, unusual layout), **or**
   - Cannot confidently split a combined statement into its constituent fields (§15), **or**
   - OCR/text extraction from an image or scanned PDF is too noisy for pattern matching to work reliably.
3. **AI must never freelance.** Every AI call must be a tightly-scoped, structured prompt that:
   - Passes it the **exact field definitions, dropdown options, and synonym/equivalence rules** relevant to the value being extracted.
   - Explicitly instructs it to return **only** a value from the allowed set (or "Not Found"), never a novel/creative answer.
   - Requests a structured (JSON) response that is then validated against the same dropdown-master/schema validation as rule-based extraction — an AI answer that fails validation is treated as "unmatched" per §14, exactly like a rule-based mismatch.
4. **No silent AI overrides.** If both rule-based and AI extraction return a value, rule-based wins unless it explicitly failed/was empty for that field.
5. **Traceability:** Log (for internal debugging, not shown to the end user) which fields were resolved by rule-based logic vs. AI fallback, to help tune the rule-based extractor over time and reduce AI dependency.

---

## 21. Cross-Cutting Correctness Rules (Read Before Implementing Extraction)

1. Never truncate an extracted value — always capture the full statement, then format/split afterward (§15).
2. Apply synonym/equivalence normalization (§10) **before** dropdown matching, so wording differences don't cause false "unmatched" flags — but never merge fields that are genuinely different (e.g., Ayurvedic Treatment ≠ AYUSH Treatment).
3. Defaults (§11) apply **only** when the source field is genuinely empty — never overwrite a present (even if unmatched) extracted value with a default; unmatched values are handled via §14, not §11.
4. Type of Proposal's Bajaj-based rule (§11) requires reliably identifying the incumbent/current insurer name from the input file — this detection must be a distinct, testable step (not folded silently into the Type of Proposal field logic) so it can be validated independently.
5. Zone, Policy Type, and Plan all have overlap/confusion risk with other fields — apply §12.2's disambiguation order strictly.
6. All master lists (dropdowns, zones, procedures, field synonyms) live in the `masters/` package as the **single source of truth** — the frontend must never hardcode a duplicate copy of any dropdown; it should fetch these from a backend endpoint or a shared generated config so the two never drift out of sync.
7. Group Size / Primary Members / SME Flag are **always derived**, never independently extracted from the RFQ text even if the RFQ mentions a headcount — the Demography Table is authoritative for these three fields (§7).

---

## 22. Testing Checklist (`test_hardening_smoke.py` should cover at minimum)

- [ ] Multi-format input batch (xlsx + pdf + image) processed together correctly.
- [ ] Password-protected file: correct password unlocks and extracts; wrong password re-prompts without breaking the batch.
- [ ] Age Mode switch OFF vs ON produces different, correct ages from the same DOB data.
- [ ] Demography header synonym recognition (e.g., "Emp Age" → Age column).
- [ ] Group Size / Primary Members / SME Flag recompute correctly at the 250-member boundary.
- [ ] Room-Rent-style combined statement splits correctly into 3 fields (§15 worked example).
- [ ] Type of Proposal correctly resolves to Own Renewal only when incumbent = Bajaj, Roll Over otherwise, New Business when empty.
- [ ] Unmatched dropdown value: default is shown + flag comment is generated + red-cross icon appears.
- [ ] Matched dropdown value: green-check icon appears.
- [ ] Procedure-wise sub-limit mapping resolves known amounts to correct Option labels, and flags unknown amounts.
- [ ] Plan-field-contains-Policy-Type case resolves to the correct output field (§12.2).
- [ ] Additional Details Table only receives genuinely unmapped fields, with no field ever appearing in two tables at once.
- [ ] AI fallback only triggers when rule-based extraction fails, and its output is still schema-validated.
- [ ] Table scroll/sticky-header CSS does not break with very large demography tables (100s of rows) or very wide RFQ tables.

---

## 23. Corrections Made to the Original Brief (For Transparency)

While consolidating, the following inconsistencies in the rough notes were resolved — flag these to confirm against the reference screenshots:

1. Demography table was described as "6 Columns" but 7 columns were listed — resolved to **7 columns**.
2. `filed_master.py` → corrected to `field_master.py`.
3. `requiremnts.txt` → corrected to `requirements.txt`.
4. `models.py` containing `schemas.py` (structurally invalid) → corrected to a `models/` package with `schemas.py` inside it.
5. "Mediclaim" spelling standardized throughout.
6. Zone C list had a stray/misplaced quote mark around "Zone D" in the raw notes — cleaned up in §12.
7. SME threshold boundary at exactly 250 was undefined ("more than 250 = NO," "less than 250 = YES") — resolved to **≤250 = YES, >250 = NO**, implemented as a single adjustable constant.
8. Added an explicit `password_handler.py` module since password handling is substantial enough to warrant its own file rather than living inside `file_reader.py`.

---

## 24. How to Use This Guidebook

1. Read this document fully before writing any code.
2. Cross-reference each section against the provided reference screenshots of the original project's UI to confirm exact visual layout, column order, and wording.
3. Build in this order: `masters/` → `models/schemas.py` → `core/` (file reading, password handling, extraction, demography engine) → `agents/` → `orchestration/orchestrator.py` → `main.py` API routes → `frontend/`.
4. Do not begin AI integration (§20) until the rule-based path is fully working end-to-end — AI is the last layer added, not the first.
5. Validate against the Testing Checklist (§22) before considering the rebuild complete.
