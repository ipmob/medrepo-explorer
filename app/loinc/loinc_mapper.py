"""
LOINC Mapper Module

This module provides utilities for mapping lab test names to LOINC codes using fuzzy matching.
It includes functions for creating and using an enhanced index for fast and accurate matching.
"""
import pandas as pd
from fuzzywuzzy import process
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import concurrent.futures
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import json
import time
from app.utils.timing import timing_decorator

from app.utils.logger import logger
from app.config.constants import LOINC_CSV_PATH, LOINC_INDEX_PATH


@timing_decorator
def find_loinc_code(
    test_name: str, 
    loinc_path: str, 
    threshold: int = 80
) -> Optional[Dict[str, Any]]:
    """
    Find the closest LOINC match for a given test name using fuzzy matching.
    
    Args:
        test_name: Name of the test to find
        loinc_path: Path to the LOINC CSV file
        threshold: Minimum match score threshold
        
    Returns:
        Dictionary with LOINC code details if a match is found, None otherwise
    """
    
    loinc_data = pd.read_csv(loinc_path, low_memory=False)
    test_names = loinc_data["COMPONENT"].tolist()
    match, score = process.extractOne(test_name, test_names)

    if score >= threshold:
        loinc_row = loinc_data[loinc_data["COMPONENT"] == match].iloc[0]
        result = {
            "LOINC_CODE": loinc_row["LOINC_NUM"],
            "TEST_NAME": loinc_row["COMPONENT"],
            "MATCH_SCORE": score,
        }
    else:
        result = None
    
    logger.info(f"LOINC code lookup for '{test_name}' completed")
    
    return result


def process_test_names(
    test_cases: Dict[str, str], 
    loinc_path: str, 
    threshold: int = 80
) -> Dict[str, Dict[str, Any]]:
    """
    Process multiple test names in parallel
    
    Args:
        test_cases: Dictionary of test cases to process
        loinc_path: Path to the LOINC CSV file
        threshold: Minimum match score threshold
        
    Returns:
        Dictionary with results for each test case
    """
    results = {}
    
    with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        future_to_test = {
            executor.submit(find_loinc_code, test_name, loinc_path, threshold): test_key 
            for test_key, test_name in test_cases.items()
        }
        
        for future in concurrent.futures.as_completed(future_to_test):
            test_key = future_to_test[future]
            try:
                result = future.result()
                results[test_key] = result if result else "No match found"
            except Exception as e:
                logger.error(f"Error processing {test_key}: {str(e)}")
                results[test_key] = f"Error: {str(e)}"
    
    return results


@timing_decorator
def save_loinc_code(loinc_path: str, index_path: str) -> None:
    """
    Create an enhanced index of LOINC codes and save it to a file.
    
    The index includes multiple fields (COMPONENT, LONG_COMMON_NAME, SHORTNAME)
    and additional metadata (CLASS) to improve matching quality.
    
    Args:
        loinc_path: Path to the LOINC CSV file
        index_path: Path to save the index file
    """
    
    logger.info(f"Creating enhanced LOINC index from {loinc_path}")
    
    # Read only necessary columns to reduce memory usage
    required_columns = ["LOINC_NUM", "COMPONENT", "LONG_COMMON_NAME", "SHORTNAME", "CLASS", "SYSTEM"]
    loinc_data = pd.read_csv(loinc_path, usecols=required_columns, low_memory=False)
    
    # Fill NaN values to avoid checks later
    loinc_data = loinc_data.fillna({
        "COMPONENT": "",
        "LONG_COMMON_NAME": "",
        "SHORTNAME": "",
        "CLASS": "",
        "SYSTEM": ""
    })
    
    # Count class frequencies
    class_counts = loinc_data["CLASS"].value_counts().to_dict()
    
    # Create index more efficiently
    loinc_index = {}
    
    # Process component entries
    component_mask = loinc_data["COMPONENT"] != ""
    component_data = loinc_data[component_mask]
    for _, row in component_data.iterrows():
        loinc_index[row["COMPONENT"]] = {
            "LOINC_CODE": row["LOINC_NUM"],
            "TEST_NAME": row["COMPONENT"],
            "LONG_NAME": row["LONG_COMMON_NAME"],
            "SHORT_NAME": row["SHORTNAME"],
            "CLASS": row["CLASS"],
            "SYSTEM": row["SYSTEM"],
            "FIELD": "COMPONENT"
        }
    
    # Process long name entries (only if significantly more informative)
    long_name_mask = (loinc_data["LONG_COMMON_NAME"] != "") & (
        (loinc_data["COMPONENT"] == "") | 
        (loinc_data["LONG_COMMON_NAME"].str.len() > loinc_data["COMPONENT"].str.len() * 1.5)
    )
    long_name_data = loinc_data[long_name_mask]
    for _, row in long_name_data.iterrows():
        loinc_index[row["LONG_COMMON_NAME"]] = {
            "LOINC_CODE": row["LOINC_NUM"],
            "TEST_NAME": row["COMPONENT"],
            "LONG_NAME": row["LONG_COMMON_NAME"],
            "SHORT_NAME": row["SHORTNAME"],
            "CLASS": row["CLASS"],
            "SYSTEM": row["SYSTEM"],
            "FIELD": "LONG_COMMON_NAME"
        }
    
    # Process short name entries (only if different from component)
    short_name_mask = (loinc_data["SHORTNAME"] != "") & (
        loinc_data["SHORTNAME"] != "deprecated") & (
        loinc_data["SHORTNAME"] != loinc_data["COMPONENT"]
    )
    short_name_data = loinc_data[short_name_mask]
    for _, row in short_name_data.iterrows():
        loinc_index[row["SHORTNAME"]] = {
            "LOINC_CODE": row["LOINC_NUM"],
            "TEST_NAME": row["COMPONENT"],
            "LONG_NAME": row["LONG_COMMON_NAME"],
            "SHORT_NAME": row["SHORTNAME"],
            "CLASS": row["CLASS"],
            "SYSTEM": row["SYSTEM"],
            "FIELD": "SHORTNAME"
        }
    
    # Log top classes
    top_classes = sorted(class_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    logger.info("Top 20 CLASS values:")
    for class_name, count in top_classes:
        logger.info(f"  {class_name}: {count} entries")
    
    # Write index to file
    with open(index_path, "w") as f:
        json.dump(loinc_index, f, indent=2)
    
    logger.info(f"LOINC index created and saved to {index_path}")
    logger.info(f"Index contains {len(loinc_index)} entries")


def load_loinc_index(index_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Load the LOINC index from a file.
    
    Args:
        index_path: Path to the index file
        
    Returns:
        Dictionary containing the LOINC index
    """
    with open(index_path, "r") as f:
        loinc_index = json.load(f)
    
    logger.info(f"Loaded LOINC index from file with {len(loinc_index)} entries from {index_path}")
    return loinc_index


@timing_decorator
def find_loinc_code_from_index(
    test_name: str, 
    loinc_index: Dict[str, Dict[str, Any]], 
    threshold: int = 80
) -> Optional[Dict[str, Any]]:
    """
    Find the closest LOINC match for a given test name using fuzzy matching
    from a pre-loaded index with improved relevance scoring.
    
    Args:
        test_name: Name of the test to find
        loinc_index: Dictionary containing the LOINC index
        threshold: Minimum match score threshold
        
    Returns:
        Dictionary with LOINC code details if a match is found, None otherwise
    """    
    test_names = list(loinc_index.keys())
    matches = process.extract(test_name, test_names, limit=10)
    
    priority_classes = {
        "HEM/BC": 10,      # Hematology/Blood Count
        "CHEM": 8,         # Chemistry
        "COAG": 8,         # Coagulation
        "ALLERGY": 5,      # Allergy
        "SERO": 5,         # Serology
        "DRUG/TOX": 3      # Drug/Toxicology
    }
    
    # More pythonic approach using max() with a key function
    filtered_matches = [(match_name, score) for match_name, score in matches if score >= threshold]
    
    if not filtered_matches:
        logger.info(f"No matches found for '{test_name}' above threshold {threshold}")
        return None
        
    def score_match(match_tuple: tuple) -> float:
        """Calculate adjusted score for a match"""
        match_name, base_score = match_tuple
        match_data = loinc_index[match_name]
        
        class_bonus = priority_classes.get(match_data["CLASS"], 0)
        field_bonus = 5 if match_data["FIELD"] == "COMPONENT" else 0
        
        system = match_data["SYSTEM"].lower()
        system_bonus = 3 if any(term in system for term in ["blood", "bld", "serum", "ser", "plasma"]) else 0
            
        return base_score + class_bonus + field_bonus + system_bonus
    
    best_match_tuple = max(filtered_matches, key=score_match, default=None)
    
    if best_match_tuple:
        best_match, best_score = best_match_tuple
        best_adjusted_score = score_match(best_match_tuple)
        
        result = loinc_index[best_match].copy()
        result["MATCH_SCORE"] = best_score
        result["ADJUSTED_SCORE"] = best_adjusted_score
    else:
        result = None
    
    logger.info(f"Enhanced LOINC code lookup for '{test_name}' completed.")
    
    return result


def process_test_names_with_index(
    test_cases: Dict[str, str], 
    loinc_index: Dict[str, Dict[str, Any]], 
    threshold: int = 80,
    max_workers: Optional[int] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Process multiple test names in parallel using the pre-loaded index
    
    Args:
        test_cases: Dictionary of test cases to process
        loinc_index: Dictionary containing the LOINC index
        threshold: Minimum match score threshold
        max_workers: Maximum number of worker processes (defaults to CPU count)
        
    Returns:
        Dictionary with results for each test case
    """
    if not test_cases:
        return {}
        
    # Use CPU count if max_workers not specified
    if max_workers is None:
        max_workers = multiprocessing.cpu_count()
        
    # For small batches, limit workers to avoid overhead
    if len(test_cases) < max_workers:
        max_workers = max(1, len(test_cases))
    
    results = {}
    
    # Use with statement to ensure proper executor cleanup
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Create futures dictionary with a dict comprehension
        futures = {
            executor.submit(find_loinc_code_from_index, test_name, loinc_index, threshold): test_key 
            for test_key, test_name in test_cases.items()
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(futures):
            test_key = futures[future]
            try:
                result = future.result()
                results[test_key] = result if result else "No match found"
            except Exception as e:
                logger.error(f"Error processing {test_key}: {str(e)}")
                results[test_key] = f"Error: {str(e)}"
    
    return results


class LoincMapper:
    """
    Class for mapping lab test names to LOINC codes.
    
    This class provides an interface for mapping lab test names to standardized LOINC codes
    using fuzzy matching with enhanced relevance scoring based on lab test characteristics.
    """
    
    def __init__(
        self, 
        loinc_path: Optional[str] = None, 
        index_path: Optional[str] = None,
        auto_initialize: bool = True
    ):
        """
        Initialize the LOINC mapper.
        
        Args:
            loinc_path: Path to the LOINC CSV file. If None, uses default path.
            index_path: Path to the index file. If None, uses default path.
            auto_initialize: Whether to automatically initialize the index on creation
        """
        self.loinc_path = loinc_path or str(LOINC_CSV_PATH)
        self.index_path = index_path or str(LOINC_INDEX_PATH)
        self.loinc_index: Optional[Dict[str, Dict[str, Any]]] = None
        
        if auto_initialize:
            self._initialize_index()
    
    @timing_decorator
    def _initialize_index(self) -> None:
        """
        Initialize the LOINC index, creating it if it doesn't exist.
        
        Raises:
            FileNotFoundError: If the LOINC CSV file doesn't exist
            IOError: If there's an error reading/writing the index
        """
        if not Path(self.loinc_path).exists():
            raise FileNotFoundError(f"LOINC CSV file not found at {self.loinc_path}")
            
        if not Path(self.index_path).exists():
            logger.info(f"Enhanced LOINC index not found at {self.index_path}, creating it...")
            save_loinc_code(self.loinc_path, self.index_path)
        
        self.loinc_index = load_loinc_index(self.index_path)
        logger.info(f"LOINC index initialized with {len(self.loinc_index or {})} entries")
    
    def ensure_index_loaded(self) -> None:
        """Ensure the index is loaded, initializing it if necessary."""
        if self.loinc_index is None:
            self._initialize_index()
    
    def find_loinc_code(
        self, 
        test_name: str, 
        threshold: int = 80
    ) -> Optional[Dict[str, Any]]:
        """
        Find the closest LOINC match for a given test name.
        
        Args:
            test_name: Name of the test to find
            threshold: Minimum match score threshold
            
        Returns:
            Dictionary with LOINC code details if a match is found, None otherwise
            
        Raises:
            RuntimeError: If the index is not initialized
        """
        self.ensure_index_loaded()
        
        if not self.loinc_index:
            raise RuntimeError("LOINC index is not initialized")
            
        return find_loinc_code_from_index(test_name, self.loinc_index, threshold)
    
    def process_test_names(
        self, 
        test_cases: Dict[str, str], 
        threshold: int = 80,
        max_workers: Optional[int] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Process multiple test names in parallel.
        
        Args:
            test_cases: Dictionary of test cases to process
            threshold: Minimum match score threshold
            max_workers: Maximum number of worker processes (defaults to CPU count)
            
        Returns:
            Dictionary with results for each test case
            
        Raises:
            RuntimeError: If the index is not initialized
        """
        self.ensure_index_loaded()
        
        if not self.loinc_index:
            raise RuntimeError("LOINC index is not initialized")
            
        return process_test_names_with_index(
            test_cases, 
            self.loinc_index, 
            threshold,
            max_workers
        )
        
    def __len__(self) -> int:
        """Return the number of entries in the LOINC index."""
        if self.loinc_index is None:
            return 0
        return len(self.loinc_index)


# Global instance that will be initialized at startup
_global_loinc_mapper = None


def get_loinc_mapper(loinc_path: Optional[str] = None, index_path: Optional[str] = None) -> LoincMapper:
    """
    Get the global LoincMapper instance, creating it if it doesn't exist.
    
    Args:
        loinc_path: Path to the LOINC CSV file. If None, uses default path.
        index_path: Path to the index file. If None, uses default path.
        
    Returns:
        An initialized LoincMapper instance
    """
    global _global_loinc_mapper
    
    if _global_loinc_mapper is None:
        _global_loinc_mapper = LoincMapper(loinc_path, index_path)
        
    return _global_loinc_mapper


if __name__ == '__main__':
    mapper = get_loinc_mapper()
    
    test_cases = {
        "interleukin_6": "Interleukin - 6 (IL-6)",
        "d_dimer": "D-DIMER (MINI VIDAS)",
        "hemoglobin": "HAEMOGLOBIN (HB)",
        "crp": "CRP (NYCOCARD)"
    }
    
    logger.info("Running test with LoincMapper class...")
    results = mapper.process_test_names(test_cases)
    
    matches = sum(1 for r in results.values() if isinstance(r, dict))
    non_matches = sum(1 for r in results.values() if r == "No match found")
    logger.info(f"Matched: {matches}/{len(results)} ({matches/len(results)*100:.1f}%)")
    logger.info(f"Not matched: {non_matches}/{len(results)} ({non_matches/len(results)*100:.1f}%)")
    
    for test_key, result in results.items():
        if isinstance(result, dict):
            print(f"Test: {test_key}")
            print(f"LOINC Code: {result.get('LOINC_CODE')}")
            print(f"Field Matched: {result.get('FIELD')}")
            print(f"Component: {result.get('TEST_NAME')}")
            print(f"Long Name: {result.get('LONG_NAME')[:80]}..." if len(result.get('LONG_NAME', '')) > 80 else f"Long Name: {result.get('LONG_NAME')}")
            print(f"Class: {result.get('CLASS')}")
            print(f"Match Score: {result.get('MATCH_SCORE')}")
            print(f"Adjusted Score: {result.get('ADJUSTED_SCORE')}")
            print("-" * 50)
        else:
            print(f"Test: {test_key}")
            print(f"Result: {result}")
            print("-" * 50)