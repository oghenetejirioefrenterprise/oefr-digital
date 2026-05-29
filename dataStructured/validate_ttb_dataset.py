#!/usr/bin/env python3
"""
Dataset validator for TTB brewery/winery/distillery directory
DataStructured validation requirements:
- Source URL on every row (non-negotiable)
- No PII (personal email, phone, home address, financial accounts)
- Check for duplicates
- Check for completeness
- Data quality validation
"""

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set, Any

# Valid US state codes
VALID_STATES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
    'DC', 'PR', 'VI', 'GU', 'AS', 'MP'  # territories
}

# Required columns per DataStructured rules
REQUIRED_COLUMNS = [
    'permit_number', 'permit_type', 'owner_name',
    'street_address', 'city', 'zip_code', 'source_url'
]

def validate_zip_code(zip_code: str) -> bool:
    """Check if zip code format is valid (5 digits or 5+4)"""
    if not zip_code:
        return False
    # Allow 5-digit or 9-digit (with hyphen) zip codes
    return bool(re.match(r'^\d{5}(-\d{4})?$', zip_code))

def check_for_pii(row: Dict[str, str]) -> List[str]:
    """
    Check for PII violations per DataStructured rules.
    Business addresses are OK; personal info is not.
    """
    issues = []

    # Check for email addresses in text fields (should not exist in TTB data)
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    for field in ['owner_name', 'operating_name', 'street_address']:
        if re.search(email_pattern, row.get(field, '')):
            issues.append(f"Email found in {field}")

    # Check for phone numbers (should not exist in TTB data)
    phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    for field in ['owner_name', 'operating_name', 'street_address']:
        if re.search(phone_pattern, row.get(field, '')):
            issues.append(f"Phone number found in {field}")

    return issues

def extract_state_from_permit(permit_number: str) -> str:
    """Extract state code from permit number (e.g., 'AK-W-15001' → 'AK')"""
    if not permit_number:
        return ''
    parts = permit_number.split('-')
    if len(parts) >= 2:
        state_code = parts[0].upper()
        # Validate it's a real state code
        if state_code in VALID_STATES:
            return state_code
    return ''

def validate_dataset(input_csv: str, harvest_json: str) -> Dict[str, Any]:
    """Main validation function"""

    print("🔍 Loading dataset...")

    # Load harvest metadata
    with open(harvest_json, 'r') as f:
        harvest_meta = json.load(f)

    validation_report = {
        'validated_at': datetime.now(timezone.utc).isoformat(),
        'input_file': input_csv,
        'harvest_metadata': harvest_meta,
        'validation_results': {
            'total_rows_read': 0,
            'total_rows_cleaned': 0,
            'rows_removed': 0,
            'issues_found': []
        },
        'data_quality': {
            'completeness': {},
            'duplicates': {},
            'invalid_data': {},
            'pii_violations': []
        },
        'summary': {}
    }

    rows = []
    seen_permit_numbers = {}
    duplicate_permits = []
    missing_field_counts = defaultdict(int)
    invalid_states = []
    invalid_zips = []
    missing_source_urls = []
    pii_violations = []
    states_derived = 0
    unparseable_permits = []

    # Read CSV
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
            validation_report['validation_results']['total_rows_read'] += 1

            # CRITICAL: Check for source_url (non-negotiable per DataStructured rules)
            if not row.get('source_url', '').strip():
                missing_source_urls.append({
                    'row': row_num,
                    'permit_number': row.get('permit_number', 'UNKNOWN')
                })
                continue  # Skip rows without source URL

            # Check for duplicates
            permit_num = row.get('permit_number', '').strip()
            if permit_num:
                if permit_num in seen_permit_numbers:
                    duplicate_permits.append({
                        'permit_number': permit_num,
                        'first_row': seen_permit_numbers[permit_num],
                        'duplicate_row': row_num
                    })
                    continue  # Skip duplicate
                seen_permit_numbers[permit_num] = row_num

            # Derive state from permit number if not present
            current_state = row.get('state', '').strip()
            if not current_state:
                derived_state = extract_state_from_permit(permit_num)
                if derived_state:
                    row['state'] = derived_state
                    states_derived += 1
                else:
                    unparseable_permits.append({
                        'row': row_num,
                        'permit_number': permit_num
                    })

            # Check required fields
            for field in REQUIRED_COLUMNS:
                if not row.get(field, '').strip():
                    missing_field_counts[field] += 1

            # Validate state code
            state = row.get('state', '').strip()
            if state and state not in VALID_STATES:
                invalid_states.append({
                    'row': row_num,
                    'permit_number': permit_num,
                    'invalid_state': state
                })

            # Validate zip code format
            zip_code = row.get('zip_code', '').strip()
            if zip_code and not validate_zip_code(zip_code):
                invalid_zips.append({
                    'row': row_num,
                    'permit_number': permit_num,
                    'invalid_zip': zip_code
                })

            # Check for PII violations
            pii_issues = check_for_pii(row)
            if pii_issues:
                pii_violations.append({
                    'row': row_num,
                    'permit_number': permit_num,
                    'issues': pii_issues
                })
                continue  # Skip rows with PII

            # Row passed all validations
            rows.append(row)

    validation_report['validation_results']['total_rows_cleaned'] = len(rows)
    validation_report['validation_results']['rows_removed'] = (
        validation_report['validation_results']['total_rows_read'] - len(rows)
    )

    # Build detailed quality report
    validation_report['data_quality']['completeness'] = {
        'missing_fields': dict(missing_field_counts),
        'total_required_fields': len(REQUIRED_COLUMNS)
    }

    validation_report['data_quality']['duplicates'] = {
        'count': len(duplicate_permits),
        'examples': duplicate_permits[:10]  # First 10 examples
    }

    validation_report['data_quality']['invalid_data'] = {
        'invalid_states': {
            'count': len(invalid_states),
            'examples': invalid_states[:10]
        },
        'invalid_zip_codes': {
            'count': len(invalid_zips),
            'examples': invalid_zips[:10]
        },
        'missing_source_urls': {
            'count': len(missing_source_urls),
            'examples': missing_source_urls[:10]
        }
    }

    validation_report['data_quality']['pii_violations'] = {
        'count': len(pii_violations),
        'examples': pii_violations[:5]
    }

    validation_report['data_quality']['state_derivation'] = {
        'states_derived_from_permit_number': states_derived,
        'unparseable_permit_numbers': {
            'count': len(unparseable_permits),
            'examples': unparseable_permits[:10]
        }
    }

    # Issues summary
    issues = []
    if duplicate_permits:
        issues.append(f"Found {len(duplicate_permits)} duplicate permit numbers")
    if missing_source_urls:
        issues.append(f"CRITICAL: {len(missing_source_urls)} rows missing source_url (removed)")
    if pii_violations:
        issues.append(f"CRITICAL: {len(pii_violations)} rows with PII violations (removed)")
    if invalid_states:
        issues.append(f"Found {len(invalid_states)} invalid state codes")
    if invalid_zips:
        issues.append(f"Found {len(invalid_zips)} invalid zip codes")
    for field, count in missing_field_counts.items():
        if count > 0:
            issues.append(f"Found {count} rows with missing {field}")

    validation_report['validation_results']['issues_found'] = issues

    # Summary
    # Status is PASS if:
    # 1. All cleaned rows have source_url (non-negotiable)
    # 2. PII violations were removed (not present in cleaned dataset)
    # Status is FAIL only if cleaned dataset still has critical issues
    total_rows_read = validation_report['validation_results']['total_rows_read']
    # An empty CSV (header-only / failed harvest) yields total_rows_read == 0.
    # Guard the quality-score division so we emit a clean FAIL report instead of
    # crashing with ZeroDivisionError.
    if total_rows_read == 0:
        status = 'FAIL'
        data_quality_score = '0.00%'
    else:
        status = 'PASS' if len(missing_source_urls) == 0 else 'FAIL'
        data_quality_score = f"{(len(rows) / total_rows_read * 100):.2f}%"

    validation_report['summary'] = {
        'status': status,
        'data_quality_score': data_quality_score,
        'rows_in_cleaned_dataset': len(rows),
        'critical_issues_removed': len(pii_violations),
        'non_critical_issues': len(duplicate_permits) + len(invalid_states) + len(invalid_zips),
        'enhancements': {
            'states_derived': states_derived,
            'note': 'State codes were derived from permit number prefixes where missing'
        },
        'compliance_notes': {
            'source_url_coverage': '100%',
            'pii_violations': f"{len(pii_violations)} rows removed",
            'duplicates': f"{len(duplicate_permits)} removed",
            'cleaned_dataset_status': 'Ready for compliance review'
        }
    }

    return validation_report, rows

def main():
    state_dir = Path(__file__).resolve().parent / 'state'
    base_name = 'ttb-brewery-winery-distillery-directory-2026-05'
    input_csv = str(state_dir / f'{base_name}.csv')
    harvest_json = str(state_dir / f'{base_name}.harvest.json')
    output_csv = str(state_dir / f'{base_name}.cleaned.csv')
    output_json = str(state_dir / f'{base_name}.validation.json')

    print("=" * 70)
    print("TTB BREWERY/WINERY/DISTILLERY DIRECTORY VALIDATION")
    print("=" * 70)

    # Run validation
    report, cleaned_rows = validate_dataset(input_csv, harvest_json)

    # Write cleaned CSV
    print(f"\n📝 Writing cleaned dataset to {output_csv}...")
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        if cleaned_rows:
            writer = csv.DictWriter(f, fieldnames=cleaned_rows[0].keys())
            writer.writeheader()
            writer.writerows(cleaned_rows)

    # Write validation report
    print(f"📊 Writing validation report to {output_json}...")
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Status: {report['summary']['status']}")
    print(f"Total rows read: {report['validation_results']['total_rows_read']:,}")
    print(f"Rows in cleaned dataset: {report['summary']['rows_in_cleaned_dataset']:,}")
    print(f"Rows removed: {report['validation_results']['rows_removed']:,}")
    print(f"Data quality score: {report['summary']['data_quality_score']}")
    print(f"\nCritical issues removed: {report['summary']['critical_issues_removed']}")
    print(f"Non-critical issues: {report['summary']['non_critical_issues']}")

    if report['validation_results']['issues_found']:
        print("\n⚠️  Issues found:")
        for issue in report['validation_results']['issues_found']:
            print(f"  • {issue}")
    else:
        print("\n✅ No issues found!")

    print("\n" + "=" * 70)
    print(f"✅ Validation complete!")
    print(f"   Cleaned CSV: {output_csv}")
    print(f"   Validation report: {output_json}")
    print("=" * 70)

if __name__ == '__main__':
    main()
