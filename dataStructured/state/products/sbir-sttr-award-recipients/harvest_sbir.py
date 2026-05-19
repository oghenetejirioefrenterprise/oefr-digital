#!/usr/bin/env python3
"""
SBIR/STTR Award Data Harvester
Filters FY2023-2025 awards from the full SBIR.gov dataset and formats for DataStructured product.
"""

import csv
import sys
from pathlib import Path
from datetime import datetime

# Target fiscal years
TARGET_YEARS = ['2023', '2024', '2025']

# Source URL template for individual awards
SBIR_AWARD_URL_TEMPLATE = "https://www.sbir.gov/sbirsearch/detail/{contract_number}"

def process_sbir_data(input_file: Path, output_file: Path):
    """
    Process SBIR award data: filter FY2023-2025, extract required fields, add source URLs.
    """

    print(f"Reading from: {input_file}")
    print(f"Writing to: {output_file}")

    # Output column mapping (our final schema)
    output_columns = [
        'company_name',
        'city',
        'state',
        'zip',
        'award_amount',
        'award_date',
        'fiscal_year',
        'awarding_agency',
        'agency_component',
        'program_phase',
        'program_type',
        'contract_number',
        'agency_tracking_number',
        'topic_code',
        'topic_title',
        'technology_area',
        'award_abstract',
        'solicitation_number',
        'solicitation_year',
        'source_url'
    ]

    rows_processed = 0
    rows_written = 0

    with open(input_file, 'r', encoding='utf-8', errors='replace') as infile:
        reader = csv.DictReader(infile)

        # First, check what the actual column names are
        print(f"\nAvailable columns in input file:")
        for i, col in enumerate(reader.fieldnames):
            print(f"  {i}: {col}")

        with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=output_columns)
            writer.writeheader()

            for row in reader:
                rows_processed += 1

                if rows_processed % 10000 == 0:
                    print(f"Processed {rows_processed} rows, written {rows_written} FY2023-2025 awards...")

                # Filter by Award Year (fiscal year)
                award_year = row.get('Award Year', '').strip()
                if award_year not in TARGET_YEARS:
                    continue

                # Extract and map fields
                contract_number = row.get('Contract', '').strip()

                output_row = {
                    'company_name': row.get('Company', '').strip(),
                    'city': row.get('City', '').strip(),
                    'state': row.get('State', '').strip(),
                    'zip': row.get('Zip', '').strip(),
                    'award_amount': row.get('Award Amount', '').strip(),
                    'award_date': row.get('Proposal Award Date', '').strip(),
                    'fiscal_year': award_year,
                    'awarding_agency': row.get('Agency', '').strip(),
                    'agency_component': row.get('Branch', '').strip(),  # Branch is the component
                    'program_phase': row.get('Phase', '').strip(),
                    'program_type': row.get('Program', '').strip(),  # SBIR or STTR
                    'contract_number': contract_number,
                    'agency_tracking_number': row.get('Agency Tracking Number', '').strip(),
                    'topic_code': row.get('Topic Code', '').strip(),
                    'topic_title': row.get('Award Title', '').strip(),  # Using Award Title as topic title
                    'technology_area': row.get('Topic Code', '').strip(),  # Topic Code serves as technology area
                    'award_abstract': row.get('Abstract', '').strip(),
                    'solicitation_number': row.get('Solicitation Number', '').strip(),
                    'solicitation_year': row.get('Solicitation Year', '').strip(),
                    'source_url': SBIR_AWARD_URL_TEMPLATE.format(contract_number=contract_number)
                }

                writer.writerow(output_row)
                rows_written += 1

    print(f"\n✅ Processing complete!")
    print(f"Total rows processed: {rows_processed:,}")
    print(f"FY2023-2025 awards written: {rows_written:,}")
    print(f"Output file: {output_file}")

    return rows_written

if __name__ == '__main__':
    base_dir = Path(__file__).parent
    input_file = base_dir / 'award_data_full.csv'
    output_file = base_dir / 'raw.csv'

    if not input_file.exists():
        print(f"ERROR: Input file not found: {input_file}")
        sys.exit(1)

    count = process_sbir_data(input_file, output_file)

    if count == 0:
        print("⚠️  WARNING: No FY2023-2025 awards found. Check Award Year values in source data.")
        sys.exit(1)
