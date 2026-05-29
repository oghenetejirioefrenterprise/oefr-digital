#!/usr/bin/env python3
"""
Validate EPA TRI dataset - standard quality checks for DataStructured
"""
import pandas as pd
import json
import re
from pathlib import Path
from datetime import datetime

def check_pii(df):
    """Check for PII patterns in the dataset"""
    pii_issues = []

    # Check for email patterns (personal emails, not just domains)
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

    # Check for phone patterns
    phone_pattern = r'\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'

    # Check for SSN patterns
    ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'

    for col in df.columns:
        # PII (emails/phones/SSNs) only appears in text/object columns. Skip
        # purely numeric columns to avoid casting and scanning them on large
        # harvests — they cannot contain '@' or hyphen-formatted PII anyway.
        if pd.api.types.is_numeric_dtype(df[col]):
            continue
        col_str = df[col].astype(str)

        # Check emails
        emails = col_str[col_str.str.contains(email_pattern, na=False, regex=True)]
        if len(emails) > 0:
            # Filter out obvious corporate/gov domains
            personal_emails = emails[~emails.str.contains(r'@(?:epa\.gov|[\w.-]+\.(?:gov|mil|edu))(?:\b|$)', na=False, regex=True)]
            if len(personal_emails) > 0:
                pii_issues.append({
                    "type": "email",
                    "column": col,
                    "count": len(personal_emails),
                    "sample": personal_emails.iloc[0] if len(personal_emails) > 0 else None
                })

        # Check phones
        phones = col_str[col_str.str.contains(phone_pattern, na=False, regex=True)]
        if len(phones) > 0:
            pii_issues.append({
                "type": "phone",
                "column": col,
                "count": len(phones),
                "sample": phones.iloc[0]
            })

        # Check SSN
        ssns = col_str[col_str.str.contains(ssn_pattern, na=False, regex=True)]
        if len(ssns) > 0:
            pii_issues.append({
                "type": "ssn",
                "column": col,
                "count": len(ssns),
                "sample": "***-**-****"  # Never show actual SSN
            })

    return pii_issues

def validate_dataset(csv_path, harvest_path, output_path):
    """Run all validation checks"""

    # Load data
    print(f"Loading {csv_path}...")
    df = pd.read_csv(csv_path)

    with open(harvest_path, 'r') as f:
        harvest_meta = json.load(f)

    print(f"Dataset loaded: {len(df)} rows, {len(df.columns)} columns")

    # 1. Row count validation
    print("Checking row count...")
    row_count = len(df)
    row_count_match = row_count == harvest_meta.get('row_count')

    # Guard against an empty CSV (header-only / failed or truncated download).
    # Without this, the completeness/duplicate percentage math below divides by
    # row_count == 0 and raises ZeroDivisionError, crashing the validation step
    # instead of emitting a clean FAIL report with a validation.json artifact.
    if row_count == 0:
        validation_report = {
            "validated_at": datetime.now().astimezone().isoformat(),
            "dataset_slug": harvest_meta.get('slug'),
            "source_file": str(csv_path),
            "harvest_metadata": str(harvest_path),
            "row_count": {
                "actual": 0,
                "expected": harvest_meta.get('row_count'),
                "match": row_count_match
            },
            "column_count": len(df.columns),
            "error": "Dataset is empty (0 rows) — failed or truncated harvest.",
            "overall_status": "FAIL"
        }
        print(f"Writing validation report to {output_path}...")
        with open(output_path, 'w') as f:
            json.dump(validation_report, f, indent=2)
        print("\n=== VALIDATION SUMMARY ===")
        print("Rows: 0 — dataset is empty")
        print("Overall status: FAIL")
        return validation_report

    # 2. Column completeness
    print("Checking column completeness...")
    completeness = {}
    for col in df.columns:
        null_count = df[col].isnull().sum()
        null_pct = (null_count / row_count) * 100
        na_count = (df[col] == 'NA').sum()
        na_pct = (na_count / row_count) * 100
        empty_count = (df[col].astype(str).str.strip() == '').sum()
        empty_pct = (empty_count / row_count) * 100

        completeness[col] = {
            "null_count": int(null_count),
            "null_pct": round(null_pct, 2),
            "na_count": int(na_count),
            "na_pct": round(na_pct, 2),
            "empty_count": int(empty_count),
            "empty_pct": round(empty_pct, 2),
            "total_missing": int(null_count + na_count + empty_count),
            "total_missing_pct": round(null_pct + na_pct + empty_pct, 2)
        }

    # 3. Duplicate check
    print("Checking for duplicates...")
    # Check for exact row duplicates
    duplicate_rows = df.duplicated().sum()
    duplicate_rows_pct = (duplicate_rows / row_count) * 100

    # Check for duplicate facility+chemical combinations (more meaningful for TRI data)
    key_cols = ['tri_facility_id', 'chemical', 'year']
    if all(col in df.columns for col in key_cols):
        duplicate_keys = df.duplicated(subset=key_cols).sum()
        duplicate_keys_pct = (duplicate_keys / row_count) * 100
    else:
        duplicate_keys = None
        duplicate_keys_pct = None

    # 4. State distribution
    print("Analyzing state distribution...")
    if 'state' in df.columns:
        state_dist = df['state'].value_counts().to_dict()
        state_count = len(state_dist)
    else:
        state_dist = {}
        state_count = 0

    # 5. PII check
    print("Checking for PII...")
    pii_issues = check_pii(df)

    # 6. Source URL validation
    print("Checking source URLs...")
    if 'source_url' in df.columns:
        missing_urls = df['source_url'].isnull().sum()
        missing_urls_pct = (missing_urls / row_count) * 100
        url_completeness = 100 - missing_urls_pct
    else:
        missing_urls = row_count
        missing_urls_pct = 100.0
        url_completeness = 0.0

    # 7. Key field validation (facility name, address, coordinates)
    print("Validating key fields...")
    key_field_issues = []

    if 'facility_name' in df.columns:
        missing_names = df['facility_name'].isnull().sum()
        if missing_names > 0:
            key_field_issues.append({
                "field": "facility_name",
                "issue": "missing_values",
                "count": int(missing_names)
            })

    if 'latitude' in df.columns and 'longitude' in df.columns:
        invalid_coords = ((df['latitude'].isnull()) | (df['longitude'].isnull())).sum()
        if invalid_coords > 0:
            key_field_issues.append({
                "field": "coordinates",
                "issue": "missing_lat_or_lon",
                "count": int(invalid_coords)
            })

        # Check for coordinates outside valid ranges
        invalid_lat = ((df['latitude'] < -90) | (df['latitude'] > 90)).sum()
        invalid_lon = ((df['longitude'] < -180) | (df['longitude'] > 180)).sum()
        if invalid_lat > 0 or invalid_lon > 0:
            key_field_issues.append({
                "field": "coordinates",
                "issue": "out_of_range",
                "count": int(invalid_lat + invalid_lon)
            })

    # Compile validation report
    print("Compiling validation report...")
    validation_report = {
        "validated_at": datetime.now().astimezone().isoformat(),
        "dataset_slug": harvest_meta.get('slug'),
        "source_file": str(csv_path),
        "harvest_metadata": str(harvest_path),

        "row_count": {
            "actual": row_count,
            "expected": harvest_meta.get('row_count'),
            "match": row_count_match
        },

        "column_count": len(df.columns),

        "completeness": completeness,

        "duplicates": {
            "exact_row_duplicates": int(duplicate_rows),
            "exact_row_duplicates_pct": round(duplicate_rows_pct, 2),
            "key_duplicates": int(duplicate_keys) if duplicate_keys is not None else None,
            "key_duplicates_pct": round(duplicate_keys_pct, 2) if duplicate_keys_pct is not None else None,
            "key_columns": key_cols if duplicate_keys is not None else None
        },

        "state_distribution": {
            "unique_states": state_count,
            "distribution": state_dist
        },

        "pii_check": {
            "issues_found": len(pii_issues),
            "details": pii_issues,
            "status": "FAIL" if len(pii_issues) > 0 else "PASS"
        },

        "source_url_completeness": {
            "missing_count": int(missing_urls),
            "missing_pct": round(missing_urls_pct, 2),
            "completeness_pct": round(url_completeness, 2),
            "status": "PASS" if url_completeness == 100.0 else "WARNING"
        },

        "key_field_validation": {
            "issues_found": len(key_field_issues),
            "details": key_field_issues
        },

        "overall_status": "PASS" if len(pii_issues) == 0 and row_count_match else "NEEDS_REVIEW"
    }

    # Write validation report
    print(f"Writing validation report to {output_path}...")
    with open(output_path, 'w') as f:
        json.dump(validation_report, f, indent=2)

    print("\n=== VALIDATION SUMMARY ===")
    print(f"Rows: {row_count:,} (match: {row_count_match})")
    print(f"Columns: {len(df.columns)}")
    print(f"States: {state_count}")
    print(f"Exact duplicates: {duplicate_rows:,} ({duplicate_rows_pct:.2f}%)")
    if duplicate_keys is not None:
        print(f"Key duplicates: {duplicate_keys:,} ({duplicate_keys_pct:.2f}%)")
    print(f"PII issues: {len(pii_issues)} ({validation_report['pii_check']['status']})")
    print(f"Source URL completeness: {url_completeness:.2f}%")
    print(f"Overall status: {validation_report['overall_status']}")

    return validation_report

if __name__ == '__main__':
    csv_path = Path('/home/oghenetejiri/apps/dataStructured/state/datasets/epa-tri-toxic-release-reporting-facilities-2026-05.csv')
    harvest_path = Path('/home/oghenetejiri/apps/dataStructured/state/datasets/epa-tri-toxic-release-reporting-facilities-2026-05.harvest.json')
    output_path = Path('/home/oghenetejiri/apps/dataStructured/state/datasets/epa-tri-toxic-release-reporting-facilities-2026-05.validation.json')

    validate_dataset(csv_path, harvest_path, output_path)
