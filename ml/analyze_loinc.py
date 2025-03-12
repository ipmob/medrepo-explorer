import pandas as pd
import os
from pathlib import Path
import numpy as np
from collections import Counter

# Path to LOINC data
base_dir = Path(__file__).parent.parent
loinc_path = os.path.join(base_dir, "data", "Loinc_2.80", "LoincTableCore", "LoincTableCore.csv")

# Load LOINC data
print(f"Loading LOINC data from {loinc_path}...")
loinc_data = pd.read_csv(loinc_path, low_memory=False)

# Print basic information
print(f"\nDataFrame shape: {loinc_data.shape}")
print(f"Columns: {', '.join(loinc_data.columns)}")

# Count null values in each column
null_counts = loinc_data.isnull().sum()
print(f"\nNull value counts:")
for col, count in null_counts.items():
    if count > 0:
        percentage = count / len(loinc_data) * 100
        print(f"  {col}: {count} ({percentage:.2f}%)")

# Analyze COMPONENT, LONG_COMMON_NAME, and SHORTNAME columns
print("\nAnalyzing potential columns for test name matching...")

# Function to analyze column values
def analyze_column(column_name):
    values = loinc_data[column_name].dropna().tolist()
    word_counter = Counter()
    
    # Count words in values
    for value in values:
        if isinstance(value, str):
            words = value.lower().split()
            word_counter.update(words)
    
    # Get most common words
    most_common_words = word_counter.most_common(10)
    
    # Count number of unique values
    unique_count = loinc_data[column_name].nunique()
    
    # Calculate average length of values
    avg_length = loinc_data[column_name].astype(str).str.len().mean()
    
    return {
        "unique_count": unique_count,
        "most_common_words": most_common_words,
        "avg_length": avg_length
    }

# Columns to analyze
columns_to_analyze = ["COMPONENT", "LONG_COMMON_NAME", "SHORTNAME", "CLASS", "PROPERTY", "SYSTEM"]

for column in columns_to_analyze:
    print(f"\n--- {column} Analysis ---")
    analysis = analyze_column(column)
    print(f"Unique values: {analysis['unique_count']} out of {len(loinc_data)}")
    print(f"Average length: {analysis['avg_length']:.2f} characters")
    print(f"Most common words:")
    for word, count in analysis['most_common_words']:
        print(f"  '{word}': {count} occurrences")

# Analyze which classes are most relevant for medical tests
print("\n--- Analysis of CLASS values for medical tests ---")
class_counts = loinc_data["CLASS"].value_counts().head(20)
print(class_counts)

# Look for examples that match our test cases
test_keywords = ["hemoglobin", "hematocrit", "platelet", "rbc", "neutrophil", "lymphocyte", 
                "monocyte", "eosinophil", "basophil", "interleukin", "dimer", "crp", "esr"]

print("\n--- Examples matching our test keywords ---")
for keyword in test_keywords:
    # Search in COMPONENT, LONG_COMMON_NAME, and SHORTNAME
    component_matches = loinc_data[loinc_data["COMPONENT"].str.lower().str.contains(keyword.lower(), na=False)]
    long_name_matches = loinc_data[loinc_data["LONG_COMMON_NAME"].str.lower().str.contains(keyword.lower(), na=False)]
    short_name_matches = loinc_data[loinc_data["SHORTNAME"].str.lower().str.contains(keyword.lower(), na=False)]
    
    # Combine unique matches
    all_matches = pd.concat([component_matches, long_name_matches, short_name_matches]).drop_duplicates(subset=["LOINC_NUM"])
    
    if not all_matches.empty:
        print(f"\nKeyword: {keyword} - Found {len(all_matches)} matches")
        # Show a few examples
        sample = all_matches.sample(min(3, len(all_matches)))
        for _, row in sample.iterrows():
            print(f"  LOINC: {row['LOINC_NUM']}")
            print(f"  COMPONENT: {row['COMPONENT']}")
            print(f"  LONG_COMMON_NAME: {row['LONG_COMMON_NAME']}")
            print(f"  SHORTNAME: {row['SHORTNAME']}")
            print(f"  CLASS: {row['CLASS']}")
            print("  " + "-" * 50) 