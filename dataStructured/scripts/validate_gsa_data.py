#!/usr/bin/env python3
"""
Data validation script for GSA Schedule Contract Holders dataset.
Role: data-steward quality gate
"""

import pandas as pd
import json
import re
from datetime import datetime
from pathlib import Path

def check_pii_concerns(row):
    """Check for potential PII in the data."""
    concerns = []

    # Email field - check if it's personal vs organizational
    email = str(row.get('email', ''))
    if email and '@' in email:
        # GSA maspmo@gsa.gov is fine (organizational POC)
        # But personal emails would be a concern
        if not email.endswith('@gsa.gov'):
            if any(provider in email.lower() for provider in ['@gmail.', '@yahoo.', '@hotmail.', '@outlook.']):
                concerns.append(f"Potential personal email: {email}")

    # Address field - these are business addresses, which is OK
    # Personal home addresses would be a concern, but these appear to be registered business locations

    return concerns

def validate_dataset(csv_path):
    """Validate the GSA dataset and generate report."""

    print("Loading dataset...")
    df = pd.read_csv(csv_path)

    total_rows = len(df)
    print(f"Total rows loaded: {total_rows}")

    # Initialize validation results
    validation = {
        "validation_date": datetime.now().isoformat(),
        "total_rows_input": total_rows,
        "issues": [],
        "warnings": [],
        "stats": {}
    }

    # 1. Check for duplicates by contract_number (primary key)
    print("\n1. Checking for duplicates...")
    duplicates_by_contract = df[df.duplicated(subset=['contract_number'], keep=False)]
    if len(duplicates_by_contract) > 0:
        dup_contracts = df['contract_number'].value_counts()
        dup_contracts = dup_contracts[dup_contracts > 1]
        validation["issues"].append({
            "type": "CRITICAL_DUPLICATES",
            "message": f"Found {len(duplicates_by_contract)} duplicate rows across {len(dup_contracts)} contract numbers",
            "details": dup_contracts.to_dict()
        })
        print(f"   ❌ CRITICAL: {len(duplicates_by_contract)} duplicate rows found")
        print(f"   Duplicate contract numbers: {len(dup_contracts)}")
    else:
        print("   ✅ No duplicates found")

    # 2. Check for missing source URLs (hard rule #3)
    print("\n2. Checking source URLs...")
    missing_source_url = df[df['source_url'].isna() | (df['source_url'] == '')]
    if len(missing_source_url) > 0:
        validation["issues"].append({
            "type": "CRITICAL_MISSING_SOURCE_URL",
            "message": f"{len(missing_source_url)} rows missing source_url",
            "rows": missing_source_url.index.tolist()
        })
        print(f"   ❌ CRITICAL: {len(missing_source_url)} rows missing source_url (violates hard rule #3)")
    else:
        print("   ✅ All rows have source_url")

    # 3. Check for PII concerns
    print("\n3. Checking for PII...")
    pii_concerns = []
    for idx, row in df.iterrows():
        concerns = check_pii_concerns(row)
        if concerns:
            pii_concerns.extend([f"Row {idx}: {c}" for c in concerns])

    if pii_concerns:
        validation["warnings"].append({
            "type": "PII_CHECK",
            "message": f"Found {len(pii_concerns)} potential PII concerns",
            "details": pii_concerns[:10]  # First 10 only
        })
        print(f"   ⚠️  {len(pii_concerns)} potential PII concerns (needs compliance review)")
    else:
        print("   ✅ No obvious PII concerns detected")

    # 4. Check data completeness
    print("\n4. Checking data completeness...")
    completeness = {}
    for col in df.columns:
        non_empty = df[col].notna().sum()
        completeness[col] = {
            "count": int(non_empty),
            "percentage": round(100 * non_empty / total_rows, 1)
        }
    validation["stats"]["completeness"] = completeness

    # Key fields that should be complete
    key_fields = ['contractor_name', 'contract_number', 'uei', 'source_url']
    for field in key_fields:
        pct = completeness[field]['percentage']
        if pct < 100:
            print(f"   ⚠️  {field}: {pct}% complete")
        else:
            print(f"   ✅ {field}: 100% complete")

    # 5. Deduplicate data
    print("\n5. Creating deduplicated dataset...")
    df_clean = df.drop_duplicates(subset=['contract_number'], keep='first')
    unique_count = len(df_clean)
    removed_count = total_rows - unique_count

    validation["stats"]["deduplication"] = {
        "original_rows": total_rows,
        "unique_rows": unique_count,
        "duplicates_removed": removed_count
    }

    print(f"   Unique contractors: {unique_count}")
    print(f"   Duplicates removed: {removed_count}")

    # 6. Validate URLs are accessible format
    print("\n6. Validating URL format...")
    url_pattern = re.compile(r'^https?://')
    invalid_urls = df_clean[~df_clean['source_url'].str.match(url_pattern, na=False)]
    if len(invalid_urls) > 0:
        validation["warnings"].append({
            "type": "INVALID_URL_FORMAT",
            "message": f"{len(invalid_urls)} rows have invalid URL format",
            "rows": invalid_urls.index.tolist()
        })
        print(f"   ⚠️  {len(invalid_urls)} invalid URL formats")
    else:
        print("   ✅ All URLs have valid format")

    # 7. Check for empty NAICS codes
    empty_naics = df_clean[df_clean['naics_codes'].isna() | (df_clean['naics_codes'] == '')]
    if len(empty_naics) > 0:
        validation["warnings"].append({
            "type": "MISSING_NAICS",
            "message": f"{len(empty_naics)} rows missing NAICS codes",
            "percentage": round(100 * len(empty_naics) / unique_count, 1)
        })
        print(f"   ⚠️  {len(empty_naics)} rows ({round(100*len(empty_naics)/unique_count, 1)}%) missing NAICS codes")

    # Overall verdict
    print("\n" + "="*60)
    critical_issues = [i for i in validation["issues"] if "CRITICAL" in i["type"]]
    if len(critical_issues) > 0:
        validation["verdict"] = "FAIL"
        validation["verdict_reason"] = f"Dataset has {len(critical_issues)} critical issues that must be resolved"
        print("❌ VALIDATION VERDICT: FAIL")
        print(f"   Reason: {validation['verdict_reason']}")
    elif len(validation["warnings"]) > 0:
        validation["verdict"] = "PASS_WITH_WARNINGS"
        validation["verdict_reason"] = f"Dataset is valid but has {len(validation['warnings'])} warnings"
        print("⚠️  VALIDATION VERDICT: PASS WITH WARNINGS")
        print(f"   Reason: {validation['verdict_reason']}")
    else:
        validation["verdict"] = "PASS"
        validation["verdict_reason"] = "Dataset passes all validation checks"
        print("✅ VALIDATION VERDICT: PASS")
        print(f"   Reason: {validation['verdict_reason']}")

    print("="*60)

    return df_clean, validation

def main():
    # Paths
    product_dir = Path("/home/oghenetejiri/apps/dataStructured/state/products/gsa-schedule-contract-holders")
    input_csv = product_dir / "dataset.csv"
    output_csv = product_dir / "dataset-clean.csv"
    validation_report = product_dir / "validation-report.json"

    # Validate and clean
    df_clean, validation = validate_dataset(input_csv)

    # Save clean dataset
    print(f"\nWriting clean dataset to {output_csv}...")
    df_clean.to_csv(output_csv, index=False)
    print(f"✅ Clean dataset saved ({len(df_clean)} rows)")

    # Save validation report
    print(f"\nWriting validation report to {validation_report}...")
    with open(validation_report, 'w') as f:
        json.dump(validation, f, indent=2)
    print("✅ Validation report saved")

    # Summary
    print("\n" + "="*60)
    print("DATA STEWARD SUMMARY")
    print("="*60)
    print(f"Input rows:       {validation['total_rows_input']}")
    print(f"Clean rows:       {validation['stats']['deduplication']['unique_rows']}")
    print(f"Removed:          {validation['stats']['deduplication']['duplicates_removed']}")
    print(f"Critical issues:  {len([i for i in validation['issues'] if 'CRITICAL' in i['type']])}")
    print(f"Warnings:         {len(validation['warnings'])}")
    print(f"Verdict:          {validation['verdict']}")
    print("="*60)

    # Next step
    if validation["verdict"] in ["PASS", "PASS_WITH_WARNINGS"]:
        print("\n✅ READY FOR COMPLIANCE REVIEW")
        print("   Next: compliance-officer should review dataset-clean.csv")
    else:
        print("\n❌ NOT READY - CRITICAL ISSUES MUST BE FIXED")
        print("   Action: data-engineer needs to re-harvest or fix data quality")

if __name__ == "__main__":
    main()
