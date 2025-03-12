import pandas as pd
from fuzzywuzzy import process
import os
from pathlib import Path
from typing import Optional, Dict, Any
import logging
import concurrent.futures
import json
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

# Configure logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

def find_loinc_code(test_name: str, loinc_path: str, threshold: int = 80) -> Optional[Dict[str, Any]]:
    """
    Find the closest LOINC match for a given test name using fuzzy matching.
    """
    import time
    start_time = time.time()
    
    # Load LOINC data within the function
    loinc_data = pd.read_csv(loinc_path, low_memory=False)
    
    # Extract all test names from the LOINC database
    test_names = loinc_data["COMPONENT"].tolist()

    # Use fuzzy matching to find the closest match
    match, score = process.extractOne(test_name, test_names)

    # Check if the match score is above the threshold
    if score >= threshold:
        # Get the corresponding LOINC code and details
        loinc_row = loinc_data[loinc_data["COMPONENT"] == match].iloc[0]
        result = {
            "LOINC_CODE": loinc_row["LOINC_NUM"],
            "TEST_NAME": loinc_row["COMPONENT"],
            "MATCH_SCORE": score,
        }
    else:
        result = None
    
    execution_time = time.time() - start_time
    logger.info(f"LOINC code lookup for '{test_name}' completed in {execution_time:.4f} seconds")
    
    return result

def process_test_names(test_cases: Dict[str, str], loinc_path: str, threshold: int = 80) -> Dict[str, Dict[str, Any]]:
    """
    Process multiple test names in parallel
    """
    results = {}
    
    with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        # Create futures for each test case
        future_to_test = {
            executor.submit(find_loinc_code, test_name, loinc_path, threshold): test_key 
            for test_key, test_name in test_cases.items()
        }
        
        # Process completed futures
        for future in concurrent.futures.as_completed(future_to_test):
            test_key = future_to_test[future]
            try:
                result = future.result()
                results[test_key] = result if result else "No match found"
            except Exception as e:
                logger.error(f"Error processing {test_key}: {str(e)}")
                results[test_key] = f"Error: {str(e)}"
    
    return results

def save_loinc_code(loinc_path: str, index_path: str) -> None:
    """
    Create an enhanced index of LOINC codes and save it to a file.
    
    The index includes multiple fields (COMPONENT, LONG_COMMON_NAME, SHORTNAME)
    and additional metadata (CLASS) to improve matching quality.
    
    Args:
        loinc_path: Path to the LOINC CSV file
        index_path: Path to save the index file
    """
    import time
    start_time = time.time()
    
    logger.info(f"Creating enhanced LOINC index from {loinc_path}")
    
    # Load LOINC data
    loinc_data = pd.read_csv(loinc_path, low_memory=False)
    
    # Create a dictionary to store the index
    loinc_index = {}
    
    # Track statistics
    class_counts = {}
    
    # Extract relevant columns
    for _, row in loinc_data.iterrows():
        loinc_code = row["LOINC_NUM"]
        component = row["COMPONENT"] if pd.notna(row["COMPONENT"]) else ""
        long_name = row["LONG_COMMON_NAME"] if pd.notna(row["LONG_COMMON_NAME"]) else ""
        short_name = row["SHORTNAME"] if pd.notna(row["SHORTNAME"]) else ""
        class_value = row["CLASS"] if pd.notna(row["CLASS"]) else ""
        system = row["SYSTEM"] if pd.notna(row["SYSTEM"]) else ""
        
        # Track class distribution
        if class_value in class_counts:
            class_counts[class_value] += 1
        else:
            class_counts[class_value] = 1
        
        # Create entry for COMPONENT
        if component:
            loinc_index[component] = {
                "LOINC_CODE": loinc_code,
                "TEST_NAME": component,
                "LONG_NAME": long_name,
                "SHORT_NAME": short_name,
                "CLASS": class_value,
                "SYSTEM": system,
                "FIELD": "COMPONENT"
            }
        
        # Create entry for LONG_COMMON_NAME if significantly different from COMPONENT
        if long_name and (not component or len(long_name) > len(component) * 1.5):
            loinc_index[long_name] = {
                "LOINC_CODE": loinc_code,
                "TEST_NAME": component,
                "LONG_NAME": long_name,
                "SHORT_NAME": short_name,
                "CLASS": class_value,
                "SYSTEM": system,
                "FIELD": "LONG_COMMON_NAME"
            }
        
        # Create entry for SHORTNAME if non-empty and not too similar to COMPONENT
        if short_name and short_name not in ["", "nan", "deprecated"] and short_name != component:
            loinc_index[short_name] = {
                "LOINC_CODE": loinc_code,
                "TEST_NAME": component,
                "LONG_NAME": long_name,
                "SHORT_NAME": short_name,
                "CLASS": class_value,
                "SYSTEM": system,
                "FIELD": "SHORTNAME"
            }
    
    # Save class distribution information
    top_classes = sorted(class_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    logger.info("Top 20 CLASS values:")
    for class_name, count in top_classes:
        logger.info(f"  {class_name}: {count} entries")
    
    # Save the index to a file
    with open(index_path, "w") as f:
        json.dump(loinc_index, f, indent=2)
    
    execution_time = time.time() - start_time
    logger.info(f"Enhanced LOINC index created and saved to {index_path} in {execution_time:.4f} seconds")
    logger.info(f"Index contains {len(loinc_index)} entries")

def load_loinc_index(index_path: str) -> Dict[str, Dict[str, str]]:
    """
    Load the LOINC index from a file.
    
    Args:
        index_path: Path to the index file
        
    Returns:
        Dictionary containing the LOINC index
    """
    with open(index_path, "r") as f:
        loinc_index = json.load(f)
    
    logger.info(f"Loaded enhanced LOINC index with {len(loinc_index)} entries from {index_path}")
    return loinc_index

def find_loinc_code_from_index(test_name: str, loinc_index: Dict[str, Dict[str, str]], threshold: int = 80) -> Optional[Dict[str, Any]]:
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
    import time
    start_time = time.time()
    
    # Extract all test names from the LOINC index
    test_names = list(loinc_index.keys())
    
    # Use fuzzy matching to find the closest match
    # Get top 5 matches to allow for class-based filtering
    matches = process.extract(test_name, test_names, limit=10)
    
    # Create a scoring system that prioritizes relevant classes for lab tests
    # Define priority classes for common lab tests
    priority_classes = {
        "HEM/BC": 10,      # Hematology/Blood Count
        "CHEM": 8,         # Chemistry
        "COAG": 8,         # Coagulation
        "ALLERGY": 5,      # Allergy
        "SERO": 5,         # Serology
        "DRUG/TOX": 3      # Drug/Toxicology
    }
    
    best_match = None
    best_score = 0
    best_adjusted_score = 0
    
    for match_name, score in matches:
        if score < threshold:
            continue
            
        match_data = loinc_index[match_name]
        
        # Calculate adjusted score based on class priority
        class_bonus = priority_classes.get(match_data["CLASS"], 0)
        
        # Add bonus for COMPONENT field which is generally more reliable
        field_bonus = 5 if match_data["FIELD"] == "COMPONENT" else 0
        
        # Adjust for SYSTEM field - prioritize matches in blood/serum
        system_bonus = 0
        if any(term in match_data["SYSTEM"].lower() for term in ["blood", "bld", "serum", "ser", "plasma"]):
            system_bonus = 3
            
        # Calculate adjusted score
        adjusted_score = score + class_bonus + field_bonus + system_bonus
        
        # Update best match if this one is better
        if adjusted_score > best_adjusted_score:
            best_match = match_name
            best_score = score
            best_adjusted_score = adjusted_score
    
    # Check if any match meets our criteria
    if best_match and best_score >= threshold:
        # Get the corresponding LOINC code and details
        result = loinc_index[best_match].copy()
        result["MATCH_SCORE"] = best_score
        result["ADJUSTED_SCORE"] = best_adjusted_score
    else:
        result = None
    
    execution_time = time.time() - start_time
    logger.info(f"Enhanced LOINC code lookup for '{test_name}' completed in {execution_time:.4f} seconds")
    
    return result

def process_test_names_with_index(test_cases: Dict[str, str], loinc_index: Dict[str, Dict[str, str]], threshold: int = 80) -> Dict[str, Dict[str, Any]]:
    """
    Process multiple test names in parallel using the pre-loaded index
    
    Args:
        test_cases: Dictionary of test cases to process
        loinc_index: Dictionary containing the LOINC index
        threshold: Minimum match score threshold
        
    Returns:
        Dictionary with results for each test case
    """
    results = {}
    
    with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        # Create futures for each test case
        future_to_test = {
            executor.submit(find_loinc_code_from_index, test_name, loinc_index, threshold): test_key 
            for test_key, test_name in test_cases.items()
        }
        
        # Process completed futures
        for future in concurrent.futures.as_completed(future_to_test):
            test_key = future_to_test[future]
            try:
                result = future.result()
                results[test_key] = result if result else "No match found"
            except Exception as e:
                logger.error(f"Error processing {test_key}: {str(e)}")
                results[test_key] = f"Error: {str(e)}"
    
    return results

def main():
    # Get the absolute path to the LOINC data
    base_dir = Path(__file__).parent.parent
    loinc_path = os.path.join(base_dir, "data", "Loinc_2.80", "LoincTableCore", "LoincTableCore.csv")
    index_path = os.path.join(base_dir, "data", "loinc_enhanced_index.json")
    
    # Check if index exists, create it if not
    if not os.path.exists(index_path):
        logger.info(f"Enhanced LOINC index not found at {index_path}, creating it...")
        save_loinc_code(loinc_path, index_path)
    
    # Load the index
    loinc_index = load_loinc_index(index_path)
    
    # Test cases dictionary
    test_cases = {
        "interleukin_6": "Interleukin - 6 (IL-6)",
        "d_dimer": "D-DIMER (MINI VIDAS)",
        "hemoglobin": "HAEMOGLOBIN (HB)",
        "hematocrit_pcv": "HEMATOCRIT/PCV",
        "rbc_count": "RBC COUNT",
        "mcv": "MCV",
        "mch": "MCH",
        "mchc": "MCHC",
        "rdw_cv": "RDW-CV",
        "tc": "TC",
        "neutrophil": "Neutrophil",
        "lymphocyte": "Lymphocyte",
        "eosinophil": "Eosinophil",
        "monocyte": "Monocyte",
        "basophil": "Basophil",
        "immature_granulocytes": "Immature Granulocytes",
        "platelet_count": "PLATELET COUNT",
        "pdw": "PDW",
        "mpv": "MPV",
        "erythrocyte_sedimentation_rate_esr": "ERYTHROCYTE SEDIMENTATION RATE (ESR)",
        "crp": "CRP (NYCOCARD)"
    }
    
    # Run with the enhanced index
    logger.info("Running test with enhanced index...")
    import time
    start_time = time.time()
    enhanced_results = process_test_names_with_index(test_cases, loinc_index)
    enhanced_time = time.time() - start_time
    logger.info(f"Enhanced index-based processing completed in {enhanced_time:.4f} seconds")
    
    # Count matches and non-matches
    matches = sum(1 for r in enhanced_results.values() if isinstance(r, dict))
    non_matches = sum(1 for r in enhanced_results.values() if r == "No match found")
    logger.info(f"Matched: {matches}/{len(enhanced_results)} ({matches/len(enhanced_results)*100:.1f}%)")
    logger.info(f"Not matched: {non_matches}/{len(enhanced_results)} ({non_matches/len(enhanced_results)*100:.1f}%)")
    
    # Use the enhanced results for output
    results = enhanced_results
    logger.info(f"Result -> : {json.dumps(results, indent=4)}")
    
    # Print results with additional information
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

if __name__ == '__main__':
    main()




# def create_and_upload_whoosh_index(json_files: List[Path], org_id: str):
#     """
#     Create a Whoosh fuzzy search index from the downloaded JSON files and upload it to S3.
#     If a value is missing for any field, capture it as an empty string.
#     Logs the number of successfully indexed documents.
#     """
#     # Create a temporary directory for the Whoosh index
#     index_dir = tempfile.mkdtemp()
    
#     # Define the schema for the fuzzy search index
#     schema = Schema(
#         id=ID(stored=True),
#         product_name=TEXT(stored=True),
#         product_description=TEXT(stored=True)
#     )
    
#     # Create the Whoosh index
#     ix = create_in(index_dir, schema)
#     writer = ix.writer()
#     # Counter for successfully indexed documents
#     successful_count = 0
#     total_count = len(json_files)
#     # Index each JSON file
#     for json_file in json_files:
#         try:
#             data = json.loads(json_file.read_text())
#             product = data.get("productItem", {})
#             # Capture missing values as empty strings
#             item_id = product.get("itemId") or ""
#             item_name = product.get("itemName") or ""
#             description = product.get("description") or ""
#             writer.add_document(
#                 id=item_id,
#                 product_name=item_name,
#                 product_description=description
#             )
#             successful_count += 1
#         except Exception as e:
#             logger.error(f"Error processing file {json_file}: {e}")
#             continue
    
#     writer.commit()
#     logger.info(f"Successfully indexed {successful_count} documents out of {total_count} to woosh index")
    
#     # Upload the Whoosh index directory to S3
#     bucket_name = os.environ['BM25_ENCODER_S3']  # using the same bucket as BM25 encoder
#     index_prefix = f"product_name_whoosh_fuzzy_index_dir/{org_id}"
    
#     for root, _, files in os.walk(index_dir):
#         for file in files:
#             local_path = os.path.join(root, file)
#             s3_key = f"{index_prefix}/{file}"
#             try:
#                 s3_client.upload_file(local_path, bucket_name, s3_key)
#             except Exception as e:
#                 logger.error(f"Error uploading {local_path} to S3: {e}")
    
#     # Clean up the temporary index directory
#     shutil.rmtree(index_dir)


# def fuzzy_search_products(query: str, org_id: str) -> List[Dict[str, Any]]:
#     """Search products using the index stored in S3"""
#     # Download the index from S3
#     index_dir = download_index_from_s3(PINECONE_BUCKET_NAME, f"product_name_whoosh_fuzzy_index_dir/{org_id}")
    
#     try:
#         # Open the index
#         ix = open_dir(index_dir)
#         searcher = ix.searcher()

#         logger.info(f"Index count: {ix.doc_count()}")
#         logger.info(f"Index schema: {ix.schema}")

#         try:
#             # Create a query parser that allows fuzzy matching
#             parser = qparser.MultifieldParser(["product_name", "product_description"], ix.schema)
#             parser.add_plugin(qparser.FuzzyTermPlugin())

#             # Add fuzzy matching to the search term
#             parsed_query = parser.parse(f"{query}~1")
#             results = searcher.search(parsed_query)
            
#             logger.info(f"Search results for '{parsed_query}':")
#             for result in results:
#                 logger.info(f"ID: {result['id']}")
#                 logger.info(f"Product Name: {result['product_name']}")
#                 try:
#                     logger.info(f"Description: {result['product_description']}")
#                 except Exception:
#                     logger.info("Description: None")
#                 logger.info("-" * 50)

#             # Convert Whoosh results to a list of dictionaries
#             fuzzy_results = [dict(result) for result in results]
#             return {"results": fuzzy_results}
#         finally:
#             searcher.close()
#     finally:
#         # Clean up the temporary directory
#         shutil.rmtree(index_dir)
