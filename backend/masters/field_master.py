DEMOGRAPHY_COLUMNS = ["Age", "Date of Birth", "Sum Insured", "Relationship", "Name", "EmpCode", "Gender"]

DEMOGRAPHY_SYNONYMS = {
    "Age": ["age", "emp age", "employee age", "member age"],
    "Date of Birth": ["date of birth", "dob", "d.o.b", "birth date", "emp dob", "dependent dob", "date_of_birth", "birth_date", "birthdate", "emp birth date", "dob/age", "dob (dd/mm/yyyy)", "dob(dd/mm/yyyy)"],
    "Sum Insured": ["sum insured", "si", "si opted", "coverage amount"],
    "Relationship": ["relationship", "relation", "relationship with employee", "relation with employee"],
    "Name": ["name", "employee name", "member name", "full name", "dependent name"],
    "EmpCode": ["empcode", "emp code", "employee code", "emp id", "employee id", "staff id"],
    "Gender": ["gender", "sex"],
}

QUOTE_SECTIONS = {
    "Quotation Details": ["Sum Insured", "Policy Tenure", "Group Category", "Type of Proposal", "Brokerage%", "Premium Payer", "Beneficiary", "Plan", "Rater Type", "Zone", "Policy Type", "Claim Servicing", "TPA"],
    "Group Policy Holder Details": ["Organization Name", "PIN Code", "State", "District", "Client Industry Type"],
    "Demography Details": ["Group Size", "Number of Primary Members", "Flagging SME"],
    "Medical Expenses Insurance Coverages": ["Pre-Existing & Specified Disease", "Initial Waiting Period", "Room Rent", "Room Rent for Normal Room", "Room Rent for ICU & Specialty Rooms", "Road Ambulance", "Air Ambulance", "Pre Hospitalization", "Post Hospitalization", "Medical Advancement Surgery", "Maternity Expenses/Benefits", "Number of Deliveries/Kids Covered", "Maternity Limit – Normal Delivery", "Maternity Limit – C Section Delivery", "Maternity Waiting Period", "AYUSH Treatment", "Co-pay on all claims", "Co-Payment on All Parental Claims only", "Co-pay for Specified Illness", "Procedure-wise Sub Limit/Disease-wise Sublimits/Sub Limit & Disease Wise Capping", "Waiver of Cataract Sublimit", "Cataract", "Cover Not Available (Quote will be referred to the Underwriter)"],
}

HOSPITAL_SECTIONS = {
    "Modern Treatments": ["Uterine Artery Embolization and HIFU", "Balloon Sinuplasty", "Deep Brain Stimulation", "Oral Chemotherapy", "Immunotherapy (incl. Monoclonal Antibody Injection)", "Intravitreal Injections (Except Lucentis)", "Intravitreal Injections", "Robotic Surgeries", "Vaporisation of the Prostate (Green/Holmium Laser)", "Bronchial Thermoplasty", "Stereotactic Radiosurgery", "Intraoperative Neuro Monitoring", "Stem Cell Therapy", "Gamma Knife/CyberKnife Surgery", "Remicade/Avastin Injection", "Biodegradable Stent", "Cochlear Implant Treatment", "Lucentis", "Functional Endoscopic Sinus Surgery", "Ayurvedic Treatment"],
    "Medical Coverage": ["Day Care Expenses", "Domiciliary Hospitalization", "Dental Treatment", "LASIK Surgery", "Refractive Error Correction", "Psychiatric Ailments/Psychiatric Treatment", "Organ Donor", "Covid-19 Treatment", "Hospitalization following Terrorism", "Internal Congenital Diseases", "External Congenital Diseases"],
    "Maternity & Newborn": ["Newborn Baby Coverage", "Newborn Baby Cover from Day One within Family Floater SI", "Maternity Complication", "Pre and Post Natal Treatment up to Maternity Limit", "Twin Delivery"],
    "Hospital Expenses": ["Anesthesia Charges", "Charges of Surgeon's Own Instruments used in Surgeries", "Assistant Surgeon/Assistant Doctor/Assistant Consultant/Attendant Charges", "Nursing Allowance", "Hospital Cash Benefit"],
    "Health & Wellness": ["Wellness Programmes/Offerings", "Health Check-Up", "Master Health Check-Up for Employees (Inbuilt Cover)", "Health Card Type"],
    "Policy Conditions": ["Claim Submission and Intimation Clause", "Proportionate Clause", "Portability", "Terrorism/Terrorism and Epidemic Outbreak", "Correction Endorsements", "Special Clause/Coverage"],
}

TERM_EQUIVALENTS = {
    "Stem Cell Therapy": ["stem cell treatment coverage"],
    "Day Care Expenses": ["day care procedures", "day care treatment"],
    "Newborn Baby Coverage": ["baby one day cover", "baby day one cover", "baby day 1 cover", "baby coverage"],
    "Dental Treatment": ["accident dental treatment"],
    "LASIK Surgery": ["lasik treatment"],
    "Hospitalization following Terrorism": ["hospitalization due to terrorism effect"],
    "Organ Donor": ["organ donor expenses"],
    "Domiciliary Hospitalization": ["domicillary hospitalization"],
    "Pre and Post Natal Treatment up to Maternity Limit": ["pre and post natal expenses"],
}

FIELD_SYNONYMS = {
    "Sum Insured": ["sum insured", "si", "family sum insured", "policy coverage amount", "sum insured / policy coverage amount", "flat sum insured"],
    "Policy Tenure": ["policy tenure", "policy period", "tenure", "policy duration", "period of insurance", "period of cover"],
    "Group Category": ["group category", "category", "family definition", "policy category"],
    "Type of Proposal": ["type of proposal", "proposal type", "business type"],
    "Brokerage%": ["brokerage", "brokerage %", "brokerage%"],
    "Premium Payer": ["premium payer"],
    "Beneficiary": ["beneficiary"],
    "Plan": ["plan", "plan type", "policy scope type", "scope of policy", "family floater"],
    "Zone": ["zone", "location zone"],
    "Policy Type": ["policy type", "product type", "group mediclaim policy", "group mediclaim polcy"],
    "Claim Servicing": ["claim servicing", "claims servicing"],
    "TPA": ["tpa", "third party administrator"],
    "Organization Name": ["organization name", "company name", "corporate name", "group mediclaim benefits", "insured name", "client name", "proposer name", "employer name", "policyholder name"],
    "PIN Code": ["pin code", "pincode", "postal code"],
    "State": ["state", "insured state", "client state", "location state"],
    "District": ["district"],
    "Client Industry Type": ["client industry type", "industry", "industry type"],
    "Pre-Existing & Specified Disease": ["pre-existing & specified disease", "pre-existing", "pre existing", "ped", "specified disease", "specified disease / all pre existing diseases", "pre existing disease waiver"],
    "Initial Waiting Period": ["initial waiting period", "30 days waiting period", "30 days, 90 days, 24 months, 36 months, 48 months, waiting period", "30 days, 90 days", "waiting period", "30 day exclusion", "first 30 days", "30 days", "exclusion period"],
    "Room Rent": ["room rent", "room rent eligibility", "single room- normal", "single room", "normal room"],
    "Room Rent for Normal Room": ["room rent for normal room", "normal room rent", "normal room", "single private room", "twin sharing"],
    "Room Rent for ICU & Specialty Rooms": ["room rent for icu & specialty rooms", "icu room rent", "icu room", "intensive care unit", "specialty room"],
    "Road Ambulance": ["road ambulance", "ambulance charges", "ambulance"],
    "Air Ambulance": ["air ambulance"],
    "Pre Hospitalization": ["pre hospitalization", "pre-hospitalization", "pre hosp", "pre-hosp"],
    "Post Hospitalization": ["post hospitalization", "post-hospitalization", "post hosp", "post-hosp"],
    "Medical Advancement Surgery": ["medical advancement surgery", "advanced medical surgery"],
    "Maternity Expenses/Benefits": ["maternity expenses/benefits", "maternity expenses", "maternity benefits", "maternity cover", "maternity"],
    "Number of Deliveries/Kids Covered": ["number of deliveries/kids covered", "number of deliveries", "kids covered", "deliveries covered", "children covered"],
    "Maternity Limit – Normal Delivery": ["maternity limit – normal delivery", "maternity limit - normal delivery", "normal delivery limit", "normal delivery", "normal- inr 50000", "normal- inr 50,000", "normal- inr"],
    "Maternity Limit – C Section Delivery": ["maternity limit – c section delivery", "maternity limit - c section delivery", "c section delivery limit", "c section", "c-section", "c section delivery", "c-section delivery", "c section- inr 50000", "c section- inr 50,000", "c section- inr 50", "c section- inr"],
    "Maternity Waiting Period": ["maternity waiting period", "maternity benefit - 9 month waiting period", "9 month waiting period", "maternity 9 month waiting period", "maternity waiting", "waiting period for maternity"],
    "AYUSH Treatment": ["ayush treatment", "ayush", "ayush coverage", "ayush coverage / treatment"],
    "Co-pay on all claims": ["co-pay on all claims", "co-payment on all claims", "copay on all claims", "co pay on all claims", "co-pay on all claim", "co payment", "co-payment", "copay"],
    "Co-Payment on All Parental Claims only": ["co-payment on all parental claims only", "co-payment on all parental claims", "co-pay on all parental claims", "copayment on parental claims", "parental co-pay", "parental copay"],
    "Co-pay for Specified Illness": ["co-pay for specified illness", "co-payment for specified illness", "co pay for specified illness", "co-pay on specified illness", "copay for specified illness"],
    "Procedure-wise Sub Limit/Disease-wise Sublimits/Sub Limit & Disease Wise Capping": ["procedure-wise sub limit", "procedure wise sub limit", "disease-wise sublimit", "disease wise capping", "sub limit & disease wise capping"],
    "Waiver of Cataract Sublimit": ["waiver of cataract sublimit"],
    "Cataract": ["cataract"],
    "Cover Not Available (Quote will be referred to the Underwriter)": ["cover not available", "referred to underwriter"],
    "Gamma Knife/CyberKnife Surgery": ["gamma knife/cyberknife surgery", "cyberknife surgery", "/ cyberknife surgery", "cyberknife", "gamma knife", "cyber knife"],
    "Stem Cell Therapy": ["stem cell therapy", "stem cell treatment coverage", "stem cell"],
}

for section in list(QUOTE_SECTIONS.values()) + list(HOSPITAL_SECTIONS.values()):
    for field in section:
        FIELD_SYNONYMS.setdefault(field, [field.lower()])
for canonical, variants in TERM_EQUIVALENTS.items():
    FIELD_SYNONYMS.setdefault(canonical, [canonical.lower()])
    FIELD_SYNONYMS[canonical].extend(variants)


TIER_INDICATOR_KEYWORDS = {
    "icu_uncapped": ["at actuals", "no capping", "full reimbursement", "actuals", "12000"],
    "normal_capped": ["single pvt ac room", "single private room", "twin sharing", "6000"]
}

FIELD_GROUPS = {
    "room_rent": {
        "parent_field": "Room Rent",
        "child_fields": {
            "Room Rent for Normal Room": {
                "keywords": ["normal", "normal room", "for normal", "single private room", "twin sharing"],
                "expected_type": "free_text"
            },
            "Room Rent for ICU & Specialty Rooms": {
                "keywords": ["icu", "specialty", "specialty room", "for icu", "intensive care"],
                "expected_type": "free_text"
            }
        }
    },
    "hospitalization": {
        "parent_field": None,
        "child_fields": {
            "Pre Hospitalization": {
                "keywords": ["pre-hosp", "pre hosp", "pre-hospitalization", "pre hospitalization", "pre-hospitalisation"],
                "expected_type": "days"
            },
            "Post Hospitalization": {
                "keywords": ["post-hosp", "post hosp", "post-hospitalization", "post hospitalization", "post-hospitalisation"],
                "expected_type": "days"
            }
        }
    },
    "maternity": {
        "parent_field": "Maternity Expenses/Benefits",
        "child_fields": {
            "Number of Deliveries/Kids Covered": {
                "keywords": ["kids covered", "number of deliveries", "deliveries covered", "children covered", "number of child deliveries", "children", "child", "kids"],
                "expected_type": "dropdown",
                "dropdown_ref": "Number of Deliveries/Kids Covered"
            },
            "Maternity Limit – Normal Delivery": {
                "keywords": ["normal delivery", "for normal"],
                "expected_type": "amount"
            },
            "Maternity Limit – C Section Delivery": {
                "keywords": ["c-section", "c section", "cesarean", "c-section delivery"],
                "expected_type": "amount"
            },
            "Maternity Waiting Period": {
                "keywords": ["waiting period", "month waiting", "waived"],
                "expected_type": "dropdown",
                "dropdown_ref": "Maternity Waiting Period"
            }
        }
    },
    "modern_treatments": {
        "parent_field": None,
        "child_fields": {
            "Stem Cell Therapy": {
                "keywords": ["stem cell therapy", "stem cell transplantation", "stem cell treatment coverage", "stem cell"],
                "expected_type": "free_text"
            },
            "Gamma Knife/CyberKnife Surgery": {
                "keywords": ["cyberknife", "cyberknife surgery", "gamma knife/cyberknife surgery"],
                "expected_type": "free_text"
            },
            "Cochlear Implant Treatment": {
                "keywords": ["cochlear implant", "cochlear implant treatment", "cochlaer implant"],
                "expected_type": "free_text"
            },
            "Oral Chemotherapy": {
                "keywords": ["oral chemotherapy"],
                "expected_type": "free_text"
            },
            "Uterine Artery Embolization and HIFU": {
                "keywords": ["uterine artery embolization", "hifu"],
                "expected_type": "free_text"
            },
            "Balloon Sinuplasty": {
                "keywords": ["balloon sinuplasty"],
                "expected_type": "free_text"
            },
            "Deep Brain Stimulation": {
                "keywords": ["deep brain stimulation"],
                "expected_type": "free_text"
            },
            "Immunotherapy (incl. Monoclonal Antibody Injection)": {
                "keywords": ["immunotherapy", "monoclonal antibody"],
                "expected_type": "free_text"
            },
            "Intravitreal Injections": {
                "keywords": ["intravitreal injections", "intra vitreal injections", "lucentis & avastin"],
                "expected_type": "free_text"
            },
            "Bronchial Thermoplasty": {
                "keywords": ["bronchial thermoplasty"],
                "expected_type": "free_text"
            },
            "Vaporisation of the Prostate (Green/Holmium Laser)": {
                "keywords": ["vaporisation of the prostate", "green laser", "holmium laser"],
                "expected_type": "free_text"
            }
        }
    }
}


