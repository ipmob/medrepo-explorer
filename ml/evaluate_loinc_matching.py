import pandas as pd
import os
from pathlib import Path
import json
import time
import logging
import re
from typing import Dict, Any, List, Tuple, Optional
import sys

# Add the parent directory to the path to import lionic_name
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.lionic_name import load_loinc_index, find_loinc_code_from_index

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def kebab_to_title(kebab_string: str) -> str:
    """Convert kebab-case to Title Case"""
    # Remove .md extension
    if kebab_string.endswith('.md'):
        kebab_string = kebab_string[:-3]
    
    # Replace hyphens with spaces and capitalize
    return ' '.join(word.capitalize() for word in kebab_string.split('-'))

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

def evaluate_loinc_matching():
    """Evaluate the LOINC matching system with a comprehensive test case"""
    # Path to LOINC index
    base_dir = Path(__file__).parent.parent
    index_path = os.path.join(base_dir, "data", "loinc_enhanced_index.json")
    
    # Load the index
    loinc_index = load_loinc_index(index_path)
    
    # Create test cases
    test_cases = create_test_cases()
    logger.info(f"Created {len(test_cases)} test cases for evaluation")
    
    # Process test cases
    start_time = time.time()
    
    results = {}
    count = 0
    total = len(test_cases)
    
    # Process test cases one by one to avoid memory issues
    for test_key, test_name in test_cases.items():
        count += 1
        if count % 10 == 0:
            logger.info(f"Processed {count}/{total} test cases")
            
        result = find_loinc_code_from_index(test_name, loinc_index)
        results[test_key] = result if result else "No match found"
    
    execution_time = time.time() - start_time
    logger.info(f"LOINC matching completed in {execution_time:.2f} seconds")
    
    # Evaluate results
    matches, non_matches, non_matched_tests, match_details = evaluate_matches(results)
    
    logger.info(f"Matched: {matches}/{len(results)} ({matches/len(results)*100:.1f}%)")
    logger.info(f"Not matched: {non_matches}/{len(results)} ({non_matches/len(results)*100:.1f}%)")
    
    # Display non-matched tests
    if non_matches > 0:
        logger.info("Non-matched tests:")
        for test in sorted(non_matched_tests):
            logger.info(f"  - {test}")
    
    # Display class distribution of matches
    class_counts = {}
    for _, _, class_val, _ in match_details:
        if class_val in class_counts:
            class_counts[class_val] += 1
        else:
            class_counts[class_val] = 1
    
    logger.info("Class distribution of matches:")
    for class_name, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {class_name}: {count} ({count/matches*100:.1f}%)")
    
    # Save results to file
    results_path = os.path.join(base_dir, "data", "loinc_matching_evaluation.json")
    with open(results_path, "w") as f:
        json.dump({
            "total_tests": len(test_cases),
            "matched": matches,
            "not_matched": non_matches,
            "match_percentage": matches/len(results)*100,
            "execution_time": execution_time,
            "non_matched_tests": non_matched_tests,
            "class_distribution": class_counts,
            "detailed_results": results
        }, f, indent=2)
    
    logger.info(f"Results saved to {results_path}")

if __name__ == "__main__":
    evaluate_loinc_matching() 