import pandas as pd
import os
from pathlib import Path
import tempfile
import shutil
import logging
import json
import time
from typing import Dict, Any, List, Optional, Tuple

# Whoosh imports
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID, KEYWORD, STORED
from whoosh.qparser import QueryParser, MultifieldParser, FuzzyTermPlugin
from whoosh import scoring

# Configure logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class LoincWhoosh:
    """Class to handle LOINC data indexing and searching using Whoosh"""
    
    def __init__(self, index_dir: str = None):
        """
        Initialize the Whoosh LOINC indexer
        
        Args:
            index_dir: Directory to store the Whoosh index. If None, a temp directory is created.
        """
        self.index_dir = index_dir if index_dir else tempfile.mkdtemp()
        self.schema = Schema(
            loinc_code=ID(stored=True),
            component=TEXT(stored=True),
            long_name=TEXT(stored=True),
            short_name=TEXT(stored=True),
            class_type=KEYWORD(stored=True),
            system=KEYWORD(stored=True),
            property=KEYWORD(stored=True),
            time_aspect=KEYWORD(stored=True),
            field_type=KEYWORD(stored=True),  # Which field this entry is from (COMPONENT, LONG_NAME, etc.)
            search_text=TEXT(stored=False)    # Combined field for searching
        )
        
        # Fields to consider when prioritizing matches
        self.priority_classes = {
            "HEM/BC": 10,      # Hematology/Blood Count
            "CHEM": 8,         # Chemistry
            "COAG": 8,         # Coagulation
            "ALLERGY": 5,      # Allergy
            "SERO": 5,         # Serology
            "DRUG/TOX": 3      # Drug/Toxicology
        }
        
        # Systems to consider when prioritizing matches
        self.priority_systems = {
            "Bld": 5,          # Blood
            "Ser": 4,          # Serum
            "Plas": 4,         # Plasma
            "Ser/Plas": 4,     # Serum or Plasma
            "Ur": 3,           # Urine
            "CSF": 2           # Cerebrospinal fluid
        }
    
    def create_index(self, loinc_path: str) -> int:
        """
        Create a Whoosh index from the LOINC CSV file
        
        Args:
            loinc_path: Path to the LOINC CSV file
            
        Returns:
            Number of documents indexed
        """
        start_time = time.time()
        logger.info(f"Creating Whoosh index for LOINC data at {self.index_dir}")
        
        # Create index directory if it doesn't exist
        os.makedirs(self.index_dir, exist_ok=True)
        
        # Create the index
        ix = create_in(self.index_dir, self.schema)
        writer = ix.writer()
        
        # Load LOINC data
        loinc_data = pd.read_csv(loinc_path, low_memory=False)
        
        # Track statistics
        indexed_count = 0
        class_counts = {}
        
        # Index each row in the CSV
        for _, row in loinc_data.iterrows():
            loinc_code = row["LOINC_NUM"] if pd.notna(row["LOINC_NUM"]) else ""
            component = row["COMPONENT"] if pd.notna(row["COMPONENT"]) else ""
            long_name = row["LONG_COMMON_NAME"] if pd.notna(row["LONG_COMMON_NAME"]) else ""
            short_name = row["SHORTNAME"] if pd.notna(row["SHORTNAME"]) else ""
            class_value = row["CLASS"] if pd.notna(row["CLASS"]) else ""
            system = row["SYSTEM"] if pd.notna(row["SYSTEM"]) else ""
            property_val = row["PROPERTY"] if pd.notna(row["PROPERTY"]) else ""
            time_aspect = row["TIME_ASPCT"] if pd.notna(row["TIME_ASPCT"]) else ""
            
            # Track class distribution
            if class_value in class_counts:
                class_counts[class_value] += 1
            else:
                class_counts[class_value] = 1
            
            # Create a combined search text field that includes all text fields
            search_text = f"{component} {long_name} {short_name}"
            
            # Add COMPONENT entry
            if component:
                writer.add_document(
                    loinc_code=loinc_code,
                    component=component,
                    long_name=long_name,
                    short_name=short_name,
                    class_type=class_value,
                    system=system,
                    property=property_val,
                    time_aspect=time_aspect,
                    field_type="COMPONENT",
                    search_text=search_text
                )
                indexed_count += 1
            
            # Add LONG_COMMON_NAME entry if significantly different from COMPONENT
            if long_name and (not component or len(long_name) > len(component) * 1.5):
                writer.add_document(
                    loinc_code=loinc_code,
                    component=component,
                    long_name=long_name,
                    short_name=short_name,
                    class_type=class_value,
                    system=system,
                    property=property_val,
                    time_aspect=time_aspect,
                    field_type="LONG_COMMON_NAME",
                    search_text=search_text
                )
                indexed_count += 1
            
            # Add SHORTNAME entry if non-empty and not too similar to COMPONENT
            if short_name and short_name not in ["", "nan", "deprecated"] and short_name != component:
                writer.add_document(
                    loinc_code=loinc_code,
                    component=component,
                    long_name=long_name,
                    short_name=short_name,
                    class_type=class_value,
                    system=system,
                    property=property_val,
                    time_aspect=time_aspect,
                    field_type="SHORTNAME",
                    search_text=search_text
                )
                indexed_count += 1
        
        # Commit the changes
        writer.commit()
        
        # Save class distribution information
        top_classes = sorted(class_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        logger.info("Top 20 CLASS values:")
        for class_name, count in top_classes:
            logger.info(f"  {class_name}: {count} entries")
        
        execution_time = time.time() - start_time
        logger.info(f"Whoosh index created with {indexed_count} entries in {execution_time:.4f} seconds")
        
        return indexed_count
    
    def search(self, test_name: str, limit: int = 10, threshold: float = 80.0) -> Optional[Dict[str, Any]]:
        """
        Search for a test name in the Whoosh index
        
        Args:
            test_name: The test name to search for
            limit: Maximum number of results to return
            threshold: Minimum score threshold (0-100)
            
        Returns:
            Dictionary with LOINC code details if a match is found, None otherwise
        """
        start_time = time.time()
        
        # Open the index
        ix = open_dir(self.index_dir)
        
        # Create a searcher with BM25F scoring (variant of BM25 that allows field weights)
        searcher = ix.searcher(weighting=scoring.BM25F())
        
        try:
            # Create a query parser for the search_text field
            parser = MultifieldParser(["component", "long_name", "short_name", "search_text"], 
                                      ix.schema)
            
            # Add fuzzy term plugin to allow for fuzzy matching
            parser.add_plugin(FuzzyTermPlugin())
            
            # Parse the query with fuzzy matching
            query = parser.parse(f"{test_name}~2")
            
            # Search for the query
            results = searcher.search(query, limit=limit)
            
            if not results:
                logger.info(f"No matches found for '{test_name}'")
                return None
            
            # Process and score results
            best_match = None
            best_score = 0
            best_adjusted_score = 0
            
            for hit in results:
                # Convert Whoosh score (0-1) to a 0-100 scale
                score = int(hit.score * 100)
                
                # Skip results below threshold
                if score < threshold:
                    continue
                
                # Get the hit data
                hit_data = dict(hit)
                
                # Calculate adjusted score with bonuses
                class_bonus = self.priority_classes.get(hit_data.get("class_type", ""), 0)
                
                # Add bonus for COMPONENT field which is generally more reliable
                field_bonus = 5 if hit_data.get("field_type") == "COMPONENT" else 0
                
                # Adjust for SYSTEM field - prioritize matches in blood/serum
                system_bonus = self.priority_systems.get(hit_data.get("system", ""), 0)
                system_text = hit_data.get("system", "").lower()
                if any(term in system_text for term in ["blood", "bld", "serum", "ser", "plasma"]):
                    system_bonus += 2
                
                # Calculate adjusted score
                adjusted_score = score + class_bonus + field_bonus + system_bonus
                
                # Update best match if this one is better
                if adjusted_score > best_adjusted_score:
                    best_match = hit_data
                    best_score = score
                    best_adjusted_score = adjusted_score
            
            # Check if we found a match
            if best_match and best_score >= threshold:
                # Format the result to match the original implementation
                result = {
                    "LOINC_CODE": best_match.get("loinc_code", ""),
                    "TEST_NAME": best_match.get("component", ""),
                    "LONG_NAME": best_match.get("long_name", ""),
                    "SHORT_NAME": best_match.get("short_name", ""),
                    "CLASS": best_match.get("class_type", ""),
                    "SYSTEM": best_match.get("system", ""),
                    "FIELD": best_match.get("field_type", ""),
                    "MATCH_SCORE": best_score,
                    "ADJUSTED_SCORE": best_adjusted_score
                }
                
                execution_time = time.time() - start_time
                logger.info(f"Whoosh LOINC code lookup for '{test_name}' completed in {execution_time:.4f} seconds")
                
                return result
            else:
                execution_time = time.time() - start_time
                logger.info(f"No suitable matches for '{test_name}' above threshold in {execution_time:.4f} seconds")
                return None
            
        finally:
            searcher.close()
    
    def process_test_cases(self, test_cases: Dict[str, str], threshold: float = 80.0) -> Dict[str, Any]:
        """
        Process multiple test cases using the Whoosh index
        
        Args:
            test_cases: Dictionary of test cases (key: test_id, value: test_name)
            threshold: Minimum score threshold (0-100)
            
        Returns:
            Dictionary of results (key: test_id, value: result dict or "No match found")
        """
        results = {}
        
        for test_key, test_name in test_cases.items():
            result = self.search(test_name, threshold=threshold)
            results[test_key] = result if result else "No match found"
        
        return results
    
    def cleanup(self):
        """Remove the temporary directory if one was created"""
        if os.path.exists(self.index_dir) and self.index_dir.startswith(tempfile.gettempdir()):
            shutil.rmtree(self.index_dir)
            logger.info(f"Cleaned up temporary directory {self.index_dir}")

def main():
    """Test the Whoosh implementation with a sample test case"""
    # Path to LOINC data
    base_dir = Path(__file__).parent.parent
    loinc_path = os.path.join(base_dir, "data", "Loinc_2.80", "LoincTableCore", "LoincTableCore.csv")
    
    # Create a permanent index directory
    index_dir = os.path.join(base_dir, "data", "loinc_whoosh_index")
    
    # Create the Whoosh indexer
    loinc_whoosh = LoincWhoosh(index_dir)
    
    # Check if index exists, create it if not
    if not os.path.exists(index_dir) or len(os.listdir(index_dir)) == 0:
        logger.info(f"Whoosh index not found at {index_dir}, creating it...")
        loinc_whoosh.create_index(loinc_path)
    
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
    
    # Process test cases
    logger.info("Processing test cases with Whoosh index...")
    start_time = time.time()
    results = loinc_whoosh.process_test_cases(test_cases)
    execution_time = time.time() - start_time
    logger.info(f"Processing completed in {execution_time:.4f} seconds")
    
    # Count matches and non-matches
    matches = sum(1 for r in results.values() if isinstance(r, dict))
    non_matches = sum(1 for r in results.values() if r == "No match found")
    logger.info(f"Matched: {matches}/{len(results)} ({matches/len(results)*100:.1f}%)")
    logger.info(f"Not matched: {non_matches}/{len(results)} ({non_matches/len(results)*100:.1f}%)")
    
    # Print results
    logger.info(f"Results: {json.dumps(results, indent=2)}")
    
    # Print detailed results
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

if __name__ == "__main__":
    main() 