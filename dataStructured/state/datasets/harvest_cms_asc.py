#!/usr/bin/env python3
"""
Harvest CMS Ambulatory Surgery Centers from Provider of Services file.
Downloads CMS POS file, filters to facility type code 17 (ASC), extracts key fields.
"""

import csv
import json
import os
import requests
from datetime import datetime
from pathlib import Path

# CMS Provider of Services iQIES File (Q1 2026)
# Contains Home Health Agency, Ambulatory Surgical Center, and Hospice providers
POS_FILE_URL = "https://data.cms.gov/sites/default/files/2026-04/90983850-6dfe-4886-9dfa-1a3890a655b3/POS_File_iQIES_Q1_2026.csv"

OUTPUT_DIR = Path("state/datasets/cms-ambulatory-surgery-centers")
TODAY = datetime.now().strftime("%Y-%m-%d")
RAW_OUTPUT = OUTPUT_DIR / f"raw-{TODAY}.csv"
HARVEST_METADATA = OUTPUT_DIR / f"harvest-{TODAY}.json"

# Field mapping from CMS POS file to our output
# CMS uses these column names (approximate - will verify on download)
FIELD_MAP = {
    'PRVDR_NUM': 'ccn',  # CMS Certification Number
    'FAC_NAME': 'facility_name',
    'ADR_VNDR_CD': 'address',
    'CITY_NAME': 'city',
    'STATE_CD': 'state',
    'ZIP_CD': 'zip',
    'PHNE_NUM': 'phone',
    'MDCR_STUS_CD': 'medicare_status',
    'ACRDTN_EFCTV_DT': 'accreditation_date',
    'GNRL_CNTL_TYPE_CD': 'control_type',
}

def download_pos_file(url: str, output_path: Path) -> Path:
    """Download CMS Provider of Services file."""
    print(f"Downloading CMS Provider of Services file from {url}...")

    response = requests.get(url, stream=True, timeout=300)
    response.raise_for_status()

    temp_file = output_path.parent / "pos_temp.csv"

    with open(temp_file, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"Downloaded {temp_file.stat().st_size / (1024*1024):.1f} MB")
    return temp_file

def filter_and_extract_asc(input_file: Path, output_file: Path) -> dict:
    """
    Filter POS file to ASC (facility type 17) and extract required fields.

    Returns metadata about the harvest.
    """
    print(f"Processing {input_file}...")

    total_rows = 0
    asc_rows = 0

    with open(input_file, 'r', encoding='utf-8', errors='replace') as infile:
        reader = csv.DictReader(infile)

        # Get actual column names from file
        actual_columns = reader.fieldnames
        print(f"Columns in file: {', '.join(actual_columns[:10])}...")

        # Open output file
        output_columns = [
            'ccn',
            'facility_name',
            'address',
            'city',
            'state',
            'zip',
            'phone',
            'medicare_status',
            'accreditation_body',
            'source_url'
        ]

        with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=output_columns)
            writer.writeheader()

            for row in reader:
                total_rows += 1

                # Filter to provider subtype code 17 (Ambulatory Surgery Center)
                provider_subtype = row.get('prvdr_sbtyp_id', '').strip()

                if provider_subtype == '17':
                    asc_rows += 1

                    # Extract and map fields (using actual column names from iQIES file)
                    output_row = {
                        'ccn': row.get('prvdr_num', '').strip(),
                        'facility_name': row.get('fac_name', '').strip(),
                        'address': row.get('st_adr', '').strip(),
                        'city': row.get('city_name', '').strip(),
                        'state': row.get('state_cd', '').strip(),
                        'zip': row.get('zip_cd', '').strip(),
                        'phone': row.get('phne_num', '').strip(),
                        'medicare_status': row.get('pgm_prtcptn_cd', '').strip(),
                        'accreditation_body': row.get('acrdtn_type_cd', '').strip(),
                        'source_url': POS_FILE_URL
                    }

                    writer.writerow(output_row)

                if total_rows % 10000 == 0:
                    print(f"Processed {total_rows:,} rows, found {asc_rows:,} ASCs...")

    return {
        'total_rows_in_source': total_rows,
        'asc_rows_extracted': asc_rows,
        'source_columns': actual_columns
    }

def main():
    """Main harvest workflow."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    harvest_start = datetime.now()

    # Download POS file
    temp_file = download_pos_file(POS_FILE_URL, OUTPUT_DIR)

    # Filter and extract ASC records
    stats = filter_and_extract_asc(temp_file, RAW_OUTPUT)

    harvest_end = datetime.now()
    duration = (harvest_end - harvest_start).total_seconds()

    # Clean up temp file
    temp_file.unlink()

    # Save harvest metadata
    metadata = {
        'dataset_name': 'cms-ambulatory-surgery-centers',
        'harvest_date': TODAY,
        'harvest_timestamp': harvest_start.isoformat(),
        'duration_seconds': duration,
        'source_url': POS_FILE_URL,
        'facility_type_code': '17',
        'facility_type_name': 'Ambulatory Surgery Center',
        'records_extracted': stats['asc_rows_extracted'],
        'total_source_records': stats['total_rows_in_source'],
        'output_file': str(RAW_OUTPUT),
        'source_columns': stats['source_columns']
    }

    with open(HARVEST_METADATA, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"\n✅ Harvest complete!")
    print(f"   - Extracted {stats['asc_rows_extracted']:,} ASC records")
    print(f"   - Saved to: {RAW_OUTPUT}")
    print(f"   - Metadata: {HARVEST_METADATA}")
    print(f"   - Duration: {duration:.1f}s")

if __name__ == '__main__':
    main()
