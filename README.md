# GMC ENCORE

GMC Quote Preparation Automation, with specification in `docs/PROJECT_SPEC.md` and a reviewable, rule-first extraction workflow.

## Windows startup

1. Install Python 3.11 or 3.12 and ensure `py` is available.
2. Unzip the project. In PowerShell, open the **GMC_ENCORE** folder.
3. Run:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   python run.py
   ```

4. Visit http://127.0.0.1:8000. For image/scanned-PDF OCR, install the Tesseract OCR executable separately and make it available on `PATH`; Python's `pytesseract` alone is not the OCR executable.
5. Populate the blank `.env` Azure variables if you have an authorized deployment. No Azure credentials are included. The deterministic extraction path does not require Azure credentials.

## Upload and processing

Upload RFQ and member-roster files together. Each workbook worksheet is inspected independently. The upload page detects protected documents and requests a password per file, then navigates to a dedicated processed-case URL. Source passwords are used transiently and not saved in the processed case. A failed password attempt returns to the same modal without discarding the upload batch.

The result page shows RFQ and demography tables, the Demography Exception and Quote Exception tabs, and Excel downloads. The **Use Policy Proposal Start Date** switch on the results page recalculates member ages without reprocessing the documents. Editing, adding, or removing a member updates group size, primary-member count, SME flag, validation findings, and Excel downloads. For large rosters the on-screen member grid shows 250 members per page; all members remain present in the case and exports.

If two RFQs state different values for the same recognized field, the field is flagged and both file/value pairs are recorded in Quote Exception for manual reconciliation. It does not choose a contractual term on the user's behalf.

## Reproducible tests

From the project root:

```powershell
python -m pytest backend/tests -q
```

The `backend/tests/fixtures` directory includes the two user-provided sample workbooks plus two **genuinely encrypted** fixture conversions: `RFQ_Sample_Protected.pdf` and `Employee_Data_Sample_Protected.xlsx`. The TEST PASSWORD FOR BOTH FIXTURES is **GMC-Test-2026**. These are testing fixtures only; never use this shared test password for real documents.

The password tests include correct-password decryption, wrong-password retry, combined PDF/Excel processing, the demography-derived quote fields, and an Excel-export consistency check. Additional mixed-format tests cover Excel, PDF, PNG, EML, and DOCX ingestion. Tests use only local inputs and do not call Azure.

## Important operational limitations

This package has automated tests for its included fixtures, but accuracy on every unseen insurer document, heavily scanned file, or encryption variant cannot be guaranteed. Review Quote Exception and Demography Exception before using a quote for underwriting. Tesseract must be installed to read scanned image-only documents. The built-in case store is **in-memory**, so cases do not survive a server restart and the application is configured for local workstation use. Do not expose it on a public network or treat it as a multi-user production service without access controls, durable case storage, data-retention policies, load tests, and a formal security review. Never upload real member details to unauthorized AI or external services.
