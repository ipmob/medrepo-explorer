"""
Examples for how to use the LOINC mapper.

This module provides examples of how to use the LOINC mapper for different use cases.
"""
import json
import time
import sys
import os
from typing import Dict, Any
from pathlib import Path

# Ensure the parent directory is in the Python path when running as a script
if __name__ == "__main__":
    # Add the project root to the Python path
    project_root = Path(__file__).parent.parent.parent
    sys.path.append(str(project_root))

# Now we can import from app modules
from app.utils.logger import logger
from app.loinc.loinc_mapper import get_loinc_mapper


def single_test_example(test_name: str) -> Dict[str, Any]:
    """
    Example of how to find a LOINC code for a single test name.
    
    Args:
        test_name: The name of the lab test to look up
        
    Returns:
        Dictionary with LOINC code details if a match is found, None otherwise
    """
    # Get the LOINC mapper instance (creates index if it doesn't exist)
    mapper = get_loinc_mapper()
    
    # Time the lookup
    start_time = time.time()
    
    # Find the LOINC code
    result = mapper.find_loinc_code(test_name)
    
    # Calculate execution time
    execution_time = time.time() - start_time
    logger.info(f"LOINC code lookup for '{test_name}' completed in {execution_time:.4f} seconds")
    
    # Print the result
    if result:
        print(f"LOINC Code: {result.get('LOINC_CODE')}")
        print(f"Field Matched: {result.get('FIELD')}")
        print(f"Component: {result.get('TEST_NAME')}")
        print(f"Match Score: {result.get('MATCH_SCORE')}")
        print(f"Adjusted Score: {result.get('ADJUSTED_SCORE')}")
    else:
        print(f"No match found for '{test_name}'")
    
    return result


def multiple_tests_example(test_cases: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    """
    Example of how to find LOINC codes for multiple test names in parallel.
    
    Args:
        test_cases: Dictionary mapping test keys to test names
        
    Returns:
        Dictionary with results for each test case
    """
    # Get the LOINC mapper instance (creates index if it doesn't exist)
    mapper = get_loinc_mapper()
    
    # Time the lookup
    start_time = time.time()
    
    # Process all test names
    results = mapper.process_test_names(test_cases)
    
    # Calculate execution time
    execution_time = time.time() - start_time
    logger.info(f"Processed {len(test_cases)} test names in {execution_time:.4f} seconds")
    
    # Count matches and non-matches
    matches = sum(1 for r in results.values() if isinstance(r, dict))
    non_matches = sum(1 for r in results.values() if r == "No match found")
    logger.info(f"Matched: {matches}/{len(results)} ({matches/len(results)*100:.1f}%)")
    logger.info(f"Not matched: {non_matches}/{len(results)} ({non_matches/len(results)*100:.1f}%)")
    
    return results


def run_examples() -> None:
    """Run all examples to demonstrate LOINC mapper functionality."""
    print("\n=== Single Test Example ===")
    single_test_example("Hemoglobin")
    
    print("\n=== Multiple Tests Example ===")
    test_cases = {
        "interleukin_6": "Interleukin - 6 (IL-6)",
        "d_dimer": "D-DIMER (MINI VIDAS)",
        "hemoglobin": "HAEMOGLOBIN (HB)",
        "hematocrit_pcv": "HEMATOCRIT/PCV",
        "rbc_count": "RBC COUNT",
        "crp": "CRP (NYCOCARD)"
    }
    
    results = multiple_tests_example(test_cases)
    
    # Pretty print a sample of the results
    sample_key = next(iter(results))
    if isinstance(results[sample_key], dict):
        print(f"\nSample result for '{sample_key}':")
        print(json.dumps(results[sample_key], indent=2))


if __name__ == "__main__":
    try:
        print("Running LOINC mapper examples...")
        run_examples()
        print("\nExamples completed successfully.")
    except Exception as e:
        print(f"Error running examples: {str(e)}")
        import traceback
        traceback.print_exc()