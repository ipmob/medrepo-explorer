import pandas as pd
import os
from pathlib import Path
import json
import time
import logging
import re
from typing import Dict, Any, List, Tuple, Optional
import sys
import concurrent.futures
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

# Add the parent directory to the path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.lionic_name import load_loinc_index, find_loinc_code_from_index
from ml.loinc_whoosh import LoincWhoosh

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_cases() -> Dict[str, str]:
    """Create a dictionary of test cases from the biomarker filenames"""
    test_cases = {
        # From the biomarker-data directory
        "activated_partial_thromboplastin_time": "Activated Partial Thromboplastin Time",
        "adiponectin": "Adiponectin",
        "albumin_in_urine": "Albumin In Urine",
        "albumin": "Albumin",
        "alkaline_phosphatase_alp": "Alkaline Phosphatase (ALP)",
        "alpha_amylase": "Alpha Amylase",
        "alt": "ALT",
        "anti_smith_antibodies": "Anti Smith Antibodies",
        "ast_blood_test": "AST Blood Test",
        "bacteria_in_urine": "Bacteria In Urine",
        "basophils": "Basophils",
        "bilirubin": "Bilirubin",
        "blood_in_urine": "Blood In Urine",
        "blood_urea_nitrogen": "Blood Urea Nitrogen",
        "calcium": "Calcium",
        "calprotectin": "Calprotectin",
        "casts_in_urine": "Casts In Urine",
        "ceruloplasmin": "Ceruloplasmin",
        "chloride_in_urine": "Chloride In Urine",
        "chloride": "Chloride",
        "cholesterol": "Cholesterol",
        "cortisol": "Cortisol",
        "creatinine_key_insights": "Creatinine",
        "crp": "CRP",
        "crystals_in_urine": "Crystals In Urine",
        "cystatin_c": "Cystatin C",
        "d_dimer": "D-Dimer",
        "dhea_s": "DHEA-S",
        "dopamine": "Dopamine",
        "egfr": "eGFR",
        "eosinophils": "Eosinophils",
        "epithelial_cells_in_urine": "Epithelial Cells In Urine",
        "erythrocyte_sedimentation_rate": "Erythrocyte Sedimentation Rate",
        "erythropoietin": "Erythropoietin",
        "estrogen": "Estrogen",
        "ethyl_glucuronide": "Ethyl Glucuronide",
        "ets_urine_test": "ETS Urine Test",
        "ferritin": "Ferritin",
        "fibrinogen": "Fibrinogen",
        "folate_blood_test": "Folate Blood Test",
        "fsh": "FSH",
        "globulin": "Globulin",
        "glucose": "Glucose",
        "growth_hormone": "Growth Hormone",
        "hematocrit": "Hematocrit",
        "hemoglobin_a1c": "Hemoglobin A1C",
        "hemoglobin": "Hemoglobin",
        "homocysteine": "Homocysteine",
        "inr_blood_test": "INR Blood Test",
        "insulin": "Insulin",
        "iron": "Iron",
        "ketones_in_blood": "Ketones In Blood",
        "ketones_in_urine": "Ketones In Urine",
        "leptin": "Leptin",
        "leukocytes_in_urine": "Leukocytes In Urine",
        "lipase": "Lipase",
        "luteinizing_hormone": "Luteinizing Hormone",
        "lymphocytes": "Lymphocytes",
        "magnesium": "Magnesium",
        "mch_blood_test": "MCH Blood Test",
        "mchc_blood_test": "MCHC Blood Test",
        "mcv": "MCV",
        "melatonin_test": "Melatonin Test",
        "mpv_blood_test": "MPV Blood Test",
        "myoglobin": "Myoglobin",
        "neutrophils": "Neutrophils",
        "nitrites_in_urine": "Nitrites In Urine",
        "oxalate_in_urine": "Oxalate In Urine",
        "parathyroid_hormone": "Parathyroid Hormone",
        "pcr_covid_test": "PCR Covid Test",
        "pdw": "PDW",
        "phosphorus_in_urine": "Phosphorus In Urine",
        "phosphorus": "Phosphorus",
        "plateletcrit_pct": "Plateletcrit PCT",
        "platelets": "Platelets",
        "potassium_in_urine": "Potassium In Urine",
        "potassium": "Potassium",
        "procalcitonin": "Procalcitonin",
        "progesterone": "Progesterone",
        "prolactin": "Prolactin",
        "prostate_specific_antigen": "Prostate Specific Antigen",
        "protein_in_urine": "Protein In Urine",
        "prothrombin_time": "Prothrombin Time",
        "rdw_blood_test": "RDW Blood Test",
        "red_blood_cell_rbc": "Red Blood Cell (RBC)",
        "selenium": "Selenium",
        "serotonin": "Serotonin",
        "sodium_in_urine": "Sodium In Urine",
        "sodium": "Sodium",
        "specific_gravity_of_urine": "Specific Gravity Of Urine",
        "testosterone_urine_test": "Testosterone Urine Test",
        "testosterone": "Testosterone",
        "total_protein": "Total Protein",
        "troponin": "Troponin",
        "tsh": "TSH",
        "urea": "Urea",
        "uric_acid": "Uric Acid",
        "urine_ph": "Urine pH",
        "urobilinogen_in_urine": "Urobilinogen In Urine",
        "vitamin_a": "Vitamin A",
        "vitamin_b1": "Vitamin B1",
        "vitamin_b12": "Vitamin B12",
        "vitamin_c": "Vitamin C",
        "vitamin_d": "Vitamin D",
        "white_blood_cell": "White Blood Cell",
        "yeast_in_urine": "Yeast In Urine",
        "zinc": "Zinc"
    }
    return test_cases

def evaluate_matches(results: Dict[str, Any]) -> Tuple[int, int, List[str], List[Tuple[str, str, str, str]]]:
    """
    Evaluate the results of the LOINC matching
    
    Returns:
        Tuple containing:
        - Number of matches
        - Number of non-matches
        - List of non-matched test names
        - List of (test_key, matched_test, class, adjusted_score) for matches
    """
    matches = 0
    non_matches = 0
    non_matched_tests = []
    match_details = []
    
    for test_key, result in results.items():
        if isinstance(result, dict):
            matches += 1
            match_details.append((
                test_key, 
                result.get("TEST_NAME", ""), 
                result.get("CLASS", ""),
                str(result.get("ADJUSTED_SCORE", ""))
            ))
        else:
            non_matches += 1
            non_matched_tests.append(test_key)
    
    return matches, non_matches, non_matched_tests, match_details

def process_test_case_with_dict_index(test_key: str, test_name: str, loinc_index: Dict[str, Dict[str, Any]], 
                                     threshold: int = 80) -> Tuple[str, Any]:
    """Process a single test case with the dictionary-based index"""
    result = find_loinc_code_from_index(test_name, loinc_index, threshold)
    return test_key, result if result else "No match found"

def process_test_case_with_whoosh(test_key: str, test_name: str, index_dir: str, 
                                 threshold: int = 80) -> Tuple[str, Any]:
    """Process a single test case with the Whoosh index"""
    # Create a Whoosh indexer without re-indexing
    loinc_whoosh = LoincWhoosh(index_dir)
    
    # Search for the test name
    result = loinc_whoosh.search(test_name, threshold=threshold)
    return test_key, result if result else "No match found"

def evaluate_dict_index_with_mp(test_cases: Dict[str, str], loinc_index: Dict[str, Dict[str, Any]], 
                              threshold: int = 80) -> Tuple[Dict[str, Any], float]:
    """
    Evaluate the dictionary-based index with multiprocessing
    
    Args:
        test_cases: Dictionary of test cases
        loinc_index: The LOINC index
        threshold: Minimum score threshold
        
    Returns:
        Tuple containing:
        - Dictionary of results
        - Execution time in seconds
    """
    start_time = time.time()
    results = {}
    
    with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        # Create futures for each test case
        future_to_test = {
            executor.submit(process_test_case_with_dict_index, test_key, test_name, loinc_index, threshold): test_key 
            for test_key, test_name in test_cases.items()
        }
        
        # Process completed futures
        completed = 0
        total = len(test_cases)
        for future in concurrent.futures.as_completed(future_to_test):
            completed += 1
            if completed % 10 == 0:
                logger.info(f"Processed {completed}/{total} tests with dictionary index")
                
            try:
                test_key, result = future.result()
                results[test_key] = result
            except Exception as e:
                test_key = future_to_test[future]
                logger.error(f"Error processing {test_key} with dictionary index: {str(e)}")
                results[test_key] = f"Error: {str(e)}"
    
    execution_time = time.time() - start_time
    return results, execution_time

def evaluate_whoosh_index_with_mp(test_cases: Dict[str, str], index_dir: str,
                                threshold: int = 80) -> Tuple[Dict[str, Any], float]:
    """
    Evaluate the Whoosh index with multiprocessing
    
    Args:
        test_cases: Dictionary of test cases
        index_dir: Path to the Whoosh index directory
        threshold: Minimum score threshold
        
    Returns:
        Tuple containing:
        - Dictionary of results
        - Execution time in seconds
    """
    start_time = time.time()
    results = {}
    
    with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        # Create futures for each test case
        future_to_test = {
            executor.submit(process_test_case_with_whoosh, test_key, test_name, index_dir, threshold): test_key 
            for test_key, test_name in test_cases.items()
        }
        
        # Process completed futures
        completed = 0
        total = len(test_cases)
        for future in concurrent.futures.as_completed(future_to_test):
            completed += 1
            if completed % 10 == 0:
                logger.info(f"Processed {completed}/{total} tests with Whoosh index")
                
            try:
                test_key, result = future.result()
                results[test_key] = result
            except Exception as e:
                test_key = future_to_test[future]
                logger.error(f"Error processing {test_key} with Whoosh index: {str(e)}")
                results[test_key] = f"Error: {str(e)}"
    
    execution_time = time.time() - start_time
    return results, execution_time

def evaluate_both_implementations():
    """
    Evaluate both implementations (dictionary-based and Whoosh-based) with the same test cases
    """
    # Path to data
    base_dir = Path(__file__).parent.parent
    loinc_path = os.path.join(base_dir, "data", "Loinc_2.80", "LoincTableCore", "LoincTableCore.csv")
    dict_index_path = os.path.join(base_dir, "data", "loinc_enhanced_index.json")
    whoosh_index_dir = os.path.join(base_dir, "data", "loinc_whoosh_index")
    
    # Make sure the Whoosh index exists
    if not os.path.exists(whoosh_index_dir) or len(os.listdir(whoosh_index_dir)) == 0:
        logger.info(f"Whoosh index not found at {whoosh_index_dir}, creating it...")
        whoosh_indexer = LoincWhoosh(whoosh_index_dir)
        whoosh_indexer.create_index(loinc_path)
    
    # Load the dictionary index
    loinc_index = load_loinc_index(dict_index_path)
    
    # Create test cases
    test_cases = create_test_cases()
    logger.info(f"Created {len(test_cases)} test cases for evaluation")
    
    # Evaluate the dictionary-based implementation with multiprocessing
    logger.info("Evaluating dictionary-based implementation with multiprocessing...")
    dict_results, dict_time = evaluate_dict_index_with_mp(test_cases, loinc_index)
    
    # Evaluate the Whoosh-based implementation with multiprocessing
    logger.info("Evaluating Whoosh-based implementation with multiprocessing...")
    whoosh_results, whoosh_time = evaluate_whoosh_index_with_mp(test_cases, whoosh_index_dir)
    
    # Analyze dictionary-based results
    dict_matches, dict_non_matches, dict_non_matched_tests, dict_match_details = evaluate_matches(dict_results)
    
    # Analyze Whoosh-based results
    whoosh_matches, whoosh_non_matches, whoosh_non_matched_tests, whoosh_match_details = evaluate_matches(whoosh_results)
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("EVALUATION SUMMARY")
    logger.info("=" * 80)
    
    logger.info("\nDictionary-based Implementation:")
    logger.info(f"Execution time: {dict_time:.2f} seconds")
    logger.info(f"Matched: {dict_matches}/{len(test_cases)} ({dict_matches/len(test_cases)*100:.1f}%)")
    logger.info(f"Not matched: {dict_non_matches}/{len(test_cases)} ({dict_non_matches/len(test_cases)*100:.1f}%)")
    
    logger.info("\nWhoosh-based Implementation:")
    logger.info(f"Execution time: {whoosh_time:.2f} seconds")
    logger.info(f"Matched: {whoosh_matches}/{len(test_cases)} ({whoosh_matches/len(test_cases)*100:.1f}%)")
    logger.info(f"Not matched: {whoosh_non_matches}/{len(test_cases)} ({whoosh_non_matches/len(test_cases)*100:.1f}%)")
    
    # Performance comparison
    if dict_time > 0:
        performance_improvement = (dict_time - whoosh_time) / dict_time * 100
        logger.info(f"\nPerformance improvement with Whoosh: {performance_improvement:.2f}%")
    
    # Match quality comparison
    if dict_matches != whoosh_matches:
        logger.info("\nMatch quality difference:")
        logger.info(f"Dictionary-only matches: {len(set(dict_non_matched_tests) - set(whoosh_non_matched_tests))}")
        logger.info(f"Whoosh-only matches: {len(set(whoosh_non_matched_tests) - set(dict_non_matched_tests))}")
    
    # Analyze class distribution for dictionary-based matches
    dict_class_counts = {}
    for _, _, class_val, _ in dict_match_details:
        if class_val in dict_class_counts:
            dict_class_counts[class_val] += 1
        else:
            dict_class_counts[class_val] = 1
    
    # Analyze class distribution for Whoosh-based matches
    whoosh_class_counts = {}
    for _, _, class_val, _ in whoosh_match_details:
        if class_val in whoosh_class_counts:
            whoosh_class_counts[class_val] += 1
        else:
            whoosh_class_counts[class_val] = 1
    
    # Save evaluation results to file
    evaluation_results = {
        "total_tests": len(test_cases),
        "dictionary_implementation": {
            "matched": dict_matches,
            "not_matched": dict_non_matches,
            "match_percentage": dict_matches/len(test_cases)*100,
            "execution_time": dict_time,
            "non_matched_tests": dict_non_matched_tests,
            "class_distribution": dict_class_counts,
            "detailed_results": dict_results
        },
        "whoosh_implementation": {
            "matched": whoosh_matches,
            "not_matched": whoosh_non_matches,
            "match_percentage": whoosh_matches/len(test_cases)*100,
            "execution_time": whoosh_time,
            "non_matched_tests": whoosh_non_matched_tests,
            "class_distribution": whoosh_class_counts,
            "detailed_results": whoosh_results
        },
        "performance_comparison": {
            "performance_improvement": (dict_time - whoosh_time) / dict_time * 100 if dict_time > 0 else "N/A",
            "dict_only_matches": list(set(dict_non_matched_tests) - set(whoosh_non_matched_tests)),
            "whoosh_only_matches": list(set(whoosh_non_matched_tests) - set(dict_non_matched_tests))
        }
    }
    
    # Save evaluation results to file
    evaluation_path = os.path.join(base_dir, "data", "loinc_implementation_comparison.json")
    with open(evaluation_path, "w") as f:
        json.dump(evaluation_results, f, indent=2)
    
    logger.info(f"\nEvaluation results saved to {evaluation_path}")

if __name__ == "__main__":
    evaluate_both_implementations() 