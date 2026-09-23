from typing import Any, Optional
from pydantic import BaseModel, Field

class FileScanResult(BaseModel):
    id: str
    filename: str
    extension: str
    category: str = "unknown"
    locked: bool = False
    size: int = 0

class TableRow(BaseModel):
    section: str = ""
    field: str
    coverage_details: Any = "Not Available"
    proposed_details: Any = "Not Available"
    source_status: str = "Not Available"
    valid_dropdown: Optional[bool] = None
    unmatched_value: Optional[str] = None

class DemographyRow(BaseModel):
    age: Optional[int] = Field(default=None, alias="Age")
    dob: Optional[str] = Field(default=None, alias="Date of Birth")
    sum_insured: Optional[Any] = Field(default=None, alias="Sum Insured")
    relationship: Optional[str] = Field(default=None, alias="Relationship")
    name: Optional[str] = Field(default=None, alias="Name")
    emp_code: Optional[str] = Field(default=None, alias="EmpCode")
    gender: Optional[str] = Field(default=None, alias="Gender")
    model_config = {"populate_by_name": True}

class ProcessSummary(BaseModel):
    total_fields: int
    auto_fill_rate: int
    review_required: int
    deviations: int
    total_tokens: int = 0
    demo_lives: int = 0

class ProcessResponse(BaseModel):
    quote_rows: list[TableRow]
    additional_rows: list[TableRow]
    hospital_rows: list[TableRow]
    demography: list[dict]
    validation_rows: list[dict]
    deviations: list[dict]
    unmatched_notes: list[str]
    summary: ProcessSummary
    extraction_mode: str = "hybrid (AI on)"
    remark_by: str = "template"
