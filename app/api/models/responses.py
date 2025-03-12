from pydantic import BaseModel
from typing import List, Optional
from pydantic import Field
from app.api.models.schema_models import TestFlag, TestAnalysis


class ProcessedTestIndicator(BaseModel):
    """Model for individual test indicators/markers with standardized fields."""
    
    # Core identification
    name: str = Field(..., description="Standardized name of the biomarker")
    display_name: str = Field(..., description="Human readable display name")
    
    # Value related fields
    value: str = Field(..., description="The measured value of the indicator")
    value_type: str = Field("string", description="Type of value (string, numeric, etc)")
    
    # Unit information
    standard_unit: str = Field(..., description="Standardized unit for the measurement")
    standard_unit_id: Optional[int] = Field(None, description="ID reference for the standard unit")
    
    # Reference range information
    reference: str = Field(..., description="Reference range or normal values")
    reference_range_min: Optional[float] = Field(None, description="Minimum value of reference range")
    reference_range_max: Optional[float] = Field(None, description="Maximum value of reference range")
    reference_range_type: str = Field("NumericRange", description="Type of reference range")
    
    # Test methodology
    methodology: Optional[str] = Field(None, description="Testing methodology used")
    
    # Result status
    flag: TestFlag = Field(default=TestFlag.UNDETERMINED, description="Flag indicating result status")
    out_of_range: Optional[bool] = Field(None, description="Indicates if value is outside reference range")
    out_direction: Optional[str] = Field(None, description="Direction of out of range (high/low)")
    
    # Additional context
    explanation_general: Optional[str] = Field(None, description="General explanation of the biomarker")
    explanation_out_of_range: Optional[str] = Field(None, description="Explanation when value is out of range")
    
    # Original values from report
    original_name: Optional[str] = Field(None, description="Original test name from report")
    original_value: Optional[str] = Field(None, description="Original value from report")
    original_unit: Optional[str] = Field(None, description="Original unit from report")
    original_reference_range: Optional[str] = Field(None, description="Original reference range from report")

    class Config:
        extra = "allow"  # Allow additional fields for future extensions

class InsightsResponse(BaseModel):
    """Response model for insights from the report."""
    insights: List[ProcessedTestIndicator] = Field(..., description="List of insights derived from the report")
    analysis: TestAnalysis = Field(..., description="Analysis of the test results")
