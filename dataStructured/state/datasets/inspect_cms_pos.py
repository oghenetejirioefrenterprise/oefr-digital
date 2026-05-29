#!/usr/bin/env python3
"""
Inspect CMS iQIES POS file to identify ASC records.
"""

import csv
import requests
from pathlib import Path
from collections import Counter

POS_FILE_URL = "https://data.cms.gov/sites/default/files/2026-04/90983850-6dfe-4886-9dfa-1a3890a655b3/POS_File_iQIES_Q1_2026.csv"

def inspect_file():
    """Download and inspect the POS file structure."""

    print("Downloading sample...")
    response = requests.get(POS_FILE_URL, stream=True, timeout=120)
    response.raise_for_status()

    # Save to temp file
    temp_file = Path("state/datasets/pos_sample.csv")
    with open(temp_file, 'wb') as f:
        downloaded = 0
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if downloaded > 50 * 1024 * 1024:  # Stop after 50MB
                break

    print(f"Downloaded {downloaded / (1024*1024):.1f} MB sample")

    # Inspect structure
    with open(temp_file, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)

        # Print column names
        print(f"\nColumn names ({len(reader.fieldnames)} total):")
        for i, col in enumerate(reader.fieldnames, 1):
            print(f"  {i:2d}. {col}")

        # Count provider types
        provider_type_counter = Counter()
        provider_subtype_counter = Counter()
        sample_rows = []

        for i, row in enumerate(reader):
            if i < 5:
                sample_rows.append(row)

            provider_type_counter[row.get('prvdr_type_id', '')] += 1
            provider_subtype_counter[row.get('prvdr_sbtyp_id', '')] += 1

            if i >= 10000:  # Sample first 10k rows
                break

        print(f"\nProvider Type Distribution (prvdr_type_id):")
        for type_id, count in provider_type_counter.most_common(20):
            print(f"  {type_id:20s}: {count:5d}")

        print(f"\nProvider Subtype Distribution (prvdr_sbtyp_id):")
        for subtype_id, count in provider_subtype_counter.most_common(20):
            print(f"  {subtype_id:20s}: {count:5d}")

        print(f"\nSample records:")
        for i, row in enumerate(sample_rows[:3], 1):
            print(f"\nRecord {i}:")
            for key in ['prvdr_num', 'fac_name', 'prvdr_type_id', 'prvdr_sbtyp_id', 'city_name', 'st_adr']:
                print(f"  {key:20s}: {row.get(key, 'N/A')}")

if __name__ == '__main__':
    inspect_file()
