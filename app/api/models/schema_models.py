from enum import Enum
from typing import Optional, Dict, List, Union
from pydantic import BaseModel, Field


class TestType(str, Enum):
    """Enumeration of medical test types based on file names."""
    
    # BLOOD_TEST_OVERVIEW = "blood-test-overview"
    BLOOD_TESTS_FOR_INFLAMMATION = "blood-tests-for-inflammation"
    CBC_BLOOD_TEST = "cbc-blood-test"
    # COAGULATION_PANEL = "coagulation-panel"
    # HORMONE_BLOOD_TEST = "hormone-blood-test"
    METABOLIC_PANEL = "metabolic-panel"
    # NUTRITIONAL_TESTS = "nutritional-tests"
    # PAP_SMEAR = "pap-smear"
    # SEMEN_ANALYSIS_PURPOSE = "semen-analysis-purpose"
    # STOOL_TEST = "stool-test"
    # SWAB_TEST = "swab-test"
    THYROID_PANEL_TEST = "thyroid-panel-test"
    # URETHRAL_SWAB = "urethral-swab"
    URINALYSIS_TEST = "urinalysis-test"
    # VIRAL_MARKER_TEST = "viral-marker-test"


class TestFlag(str, Enum):
    """Standardized flags for test results."""
    
    NORMAL = "normal"
    LOW = "low"
    HIGH = "high"
    CRITICAL_LOW = "critical_low"
    CRITICAL_HIGH = "critical_high"
    UNDETERMINED = "undetermined"


class TestIndicator(BaseModel):
    """Model for individual test indicators/markers."""
    
    # Standard fields (processed)
    value: str = Field(..., description="The measured value of the indicator")
    reference: str = Field(..., description="Reference range or normal values")
    methodology: Optional[str] = Field(None, description="Testing methodology used")
    flag: TestFlag = Field(default=TestFlag.UNDETERMINED, description="Flag indicating result status")
    
    # Original values exactly as they appear in the report
    original_name: Optional[str] = Field(None, description="Original test name exactly as shown in report")
    original_value: Optional[str] = Field(None, description="Original value string exactly as shown in report")
    original_unit: Optional[str] = Field(None, description="Original unit as shown in report")
    original_reference: Optional[str] = Field(None, description="Original reference range as shown in report")
    
    class Config:
        extra = "allow"  # Allow additional fields for future extensions


class TestAnalysis(BaseModel):
    """Analysis of test results with summary and recommendations."""
    
    summary: str = Field(..., description="Summary of test results and findings")
    recommendations: Optional[str] = Field(None, description="Clinical recommendations based on results")
    markdown: Optional[str] = Field(None, description="Markdown formatted report for display")


class PatientDetails(BaseModel):
    """Basic patient identification and demographic information."""
    
    name: str = Field(..., description="Patient's full name")
    age: int = Field(..., description="Patient's age in years")
    sex: str = Field(..., description="Patient's biological sex")
    reg_no: Optional[str] = Field(None, description="Registration or patient ID number")
    registration_date: Optional[str] = Field(None, description="Date of registration")


class ReportDetails(BaseModel):
    """Administrative details about the medical report."""
    
    request_no: Optional[str] = Field(None, description="Request number")
    bill_no: Optional[str] = Field(None, description="Billing number")
    referral_by: Optional[str] = Field(None, description="Referring doctor or entity")
    reporting_date: Optional[str] = Field(None, description="Date of report generation")
    specimen: Optional[Dict[str, str]] = Field(None, description="Details about the specimen")


class LaboratoryDetails(BaseModel):
    """Information about the laboratory and verification."""
    
    entered_by: Optional[str] = Field(None, description="Person who entered the data")
    verified_by: Optional[str] = Field(None, description="Person who verified the data")
    date: Optional[str] = Field(None, description="Date of verification")
    time: Optional[str] = Field(None, description="Time of verification")
    final_report: Optional[Dict[str, str]] = Field(None, description="Final report details including signature")


class TestResults(BaseModel):
    """Complete test result including type, indicators, and analysis."""
    
    test_type: TestType = Field(..., description="Type of medical test performed")
    indicators: Dict[str, TestIndicator] = Field(..., description="Test indicators with their values and references")
    analysis: Optional[TestAnalysis] = Field(None, description="Analysis of the test results")


class MedicalReport(BaseModel):
    """Complete medical report model incorporating all components."""
    
    patient_details: PatientDetails = Field(..., description="Patient identification and demographic information")
    report_details: Optional[ReportDetails] = Field(
        default_factory=lambda: ReportDetails(request_no=""), 
        description="Administrative details about the medical report"
    )
    laboratory_details: Optional[LaboratoryDetails] = Field(
        default_factory=lambda: LaboratoryDetails(),
        description="Information about the laboratory and verification details"
    )
    test_results: TestResults = Field(..., description="Complete test results including indicators and analysis")