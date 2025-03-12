"""
LOINC API Endpoints

This module provides API endpoints for LOINC code mapping functionality.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from app.utils.logger import logger
from app.loinc.loinc_mapper import get_loinc_mapper

router = APIRouter()


class TestNameRequest(BaseModel):
    """Request model for a single test name lookup."""
    test_name: str
    threshold: Optional[int] = 80


class BatchTestNameRequest(BaseModel):
    """Request model for batch test name lookup."""
    test_cases: Dict[str, str]
    threshold: Optional[int] = 80


class LoincResult(BaseModel):
    """Response model for LOINC code lookup results."""
    loinc_code: Optional[str] = None
    test_name: Optional[str] = None
    long_name: Optional[str] = None
    class_value: Optional[str] = None
    system: Optional[str] = None
    match_score: Optional[int] = None
    adjusted_score: Optional[int] = None
    field_matched: Optional[str] = None
    found: bool = False
    error: Optional[str] = None


@router.post("/lookup", response_model=LoincResult)
async def lookup_loinc_code(request: TestNameRequest) -> LoincResult:
    """
    Look up a LOINC code for a given test name.
    
    Args:
        request: The request containing the test name and optional threshold
        
    Returns:
        The LOINC code lookup result
    """
    try:
        mapper = get_loinc_mapper()
        result = mapper.find_loinc_code(request.test_name, request.threshold)
        
        if result is None:
            return LoincResult(
                found=False,
                error=f"No match found for test name: {request.test_name}"
            )
        
        return LoincResult(
            loinc_code=result.get("LOINC_CODE"),
            test_name=result.get("TEST_NAME"),
            long_name=result.get("LONG_NAME"),
            class_value=result.get("CLASS"),
            system=result.get("SYSTEM"),
            match_score=result.get("MATCH_SCORE"),
            adjusted_score=result.get("ADJUSTED_SCORE"),
            field_matched=result.get("FIELD"),
            found=True
        )
        
    except Exception as e:
        logger.error(f"Error looking up LOINC code: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error looking up LOINC code: {str(e)}")


@router.post("/batch-lookup", response_model=Dict[str, LoincResult])
async def batch_lookup_loinc_codes(request: BatchTestNameRequest) -> Dict[str, LoincResult]:
    """
    Look up LOINC codes for multiple test names in a batch.
    
    Args:
        request: The request containing the test cases and optional threshold
        
    Returns:
        Dictionary mapping test keys to LOINC code lookup results
    """
    try:
        mapper = get_loinc_mapper()
        batch_results = mapper.process_test_names(request.test_cases, request.threshold)
        
        response_results = {}
        for key, result in batch_results.items():
            if result == "No match found":
                response_results[key] = LoincResult(
                    found=False,
                    error=f"No match found for test name: {request.test_cases[key]}"
                )
            elif isinstance(result, str) and result.startswith("Error:"):
                response_results[key] = LoincResult(
                    found=False,
                    error=result
                )
            else:
                response_results[key] = LoincResult(
                    loinc_code=result.get("LOINC_CODE"),
                    test_name=result.get("TEST_NAME"),
                    long_name=result.get("LONG_NAME"),
                    class_value=result.get("CLASS"),
                    system=result.get("SYSTEM"),
                    match_score=result.get("MATCH_SCORE"),
                    adjusted_score=result.get("ADJUSTED_SCORE"),
                    field_matched=result.get("FIELD"),
                    found=True
                )
        
        return response_results
        
    except Exception as e:
        logger.error(f"Error in batch lookup of LOINC codes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in batch lookup of LOINC codes: {str(e)}") 