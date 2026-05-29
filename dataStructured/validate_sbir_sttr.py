#!/usr/bin/env python3
"""
Data Steward Validation Script for SBIR/STTR Award Recipients
Validates raw.csv against quality gates and produces clean.csv
"""

import csv
import re
from pathlib import Path
from urllib.parse import urlparse
from collections import defaultdict

# PII Detection Patterns
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
# Phone pattern that excludes ZIP+4 format (must not be preceded/followed by digits)
PHONE_PATTERN = re.compile(r'(?<!\d)\d{3}[-.]?\d{3}[-.]?\d{4}(?!\d)')
SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
ZIP_PLUS4_PATTERN = re.compile(r'\b\d{5}-\d{4}\b')  # Exclude these from phone checks

# Validation Results
validation_results = {
    'total_rows': 0,
    'deduped_rows': 0,
    'duplicates_removed': 0,
    'invalid_urls': [],
    'missing_critical_fields': [],
    'pii_violations': [],
    'empty_source_urls': 0,
    'malformed_urls': 0,
    'null_company_names': 0,
    'null_award_amounts': 0,
    'null_agencies': 0,
}

def is_valid_url(url):
    """Check if URL is well-formed"""
    if not url or not url.strip():
        return False
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
    except (ValueError, TypeError):
        return False

def check_pii(row_data):
    """Scan row for PII violations"""
    violations = []

    # Separate scanning for different field types
    # Business info (company, city, state, zip) should NOT be scanned for PII
    pii_scan_fields = ['award_abstract', 'topic_title', 'technology_area']
    text_to_scan = ' '.join(str(row_data.get(field, '')) for field in pii_scan_fields)

    # Check for email in abstracts/descriptions (personal emails only)
    email_matches = EMAIL_PATTERN.findall(text_to_scan)
    # Filter out generic/institutional emails
    personal_emails = [e for e in email_matches if not any(domain in e.lower() for domain in
        ['@sbir.gov', '@nsf.gov', '@nasa.gov', '@energy.gov', '@defense.gov', '@example.com', '@company.com'])]
    if personal_emails:
        violations.append(f'EMAIL_DETECTED: {personal_emails[0]}')

    # Check for phone numbers (excluding ZIP codes)
    # First, remove all ZIP+4 codes to avoid false positives
    text_without_zips = ZIP_PLUS4_PATTERN.sub('', text_to_scan)
    phone_matches = PHONE_PATTERN.findall(text_without_zips)
    if phone_matches:
        # Additional filter: ignore if it's clearly a technical number or model number
        # Real phone numbers usually appear with context like "call", "contact", "phone", etc.
        has_phone_context = any(keyword in text_to_scan.lower() for keyword in
            ['call', 'contact', 'phone', 'tel:', 'telephone', 'mobile'])
        if has_phone_context:
            violations.append(f'PHONE_DETECTED: {phone_matches[0]}')

    # Check for SSN
    if SSN_PATTERN.search(text_to_scan):
        violations.append('SSN_DETECTED')

    # Check for explicit residential address language (not just business addresses)
    text_lower = text_to_scan.lower()
    residential_indicators = ['residential address', 'home address', 'personal address', 'home phone', 'personal phone']
    if any(indicator in text_lower for indicator in residential_indicators):
        violations.append('RESIDENTIAL_ADDRESS_DETECTED')

    return violations

def validate_critical_fields(row):
    """Check for null/empty critical fields"""
    issues = []

    if not row.get('company_name', '').strip():
        issues.append('NULL_COMPANY_NAME')
        validation_results['null_company_names'] += 1

    if not row.get('award_amount', '').strip():
        issues.append('NULL_AWARD_AMOUNT')
        validation_results['null_award_amounts'] += 1

    if not row.get('awarding_agency', '').strip():
        issues.append('NULL_AGENCY')
        validation_results['null_agencies'] += 1

    return issues

def main():
    base_dir = Path(__file__).parent / 'state/products/sbir-sttr-award-recipients'
    raw_csv = base_dir / 'raw.csv'
    clean_csv = base_dir / 'clean.csv'

    print("🔍 SBIR/STTR Dataset Validation Starting...")
    print(f"📂 Reading: {raw_csv}")

    # Track unique contract numbers
    seen_contracts = {}
    clean_rows = []

    with open(raw_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        for idx, row in enumerate(reader, start=1):
            validation_results['total_rows'] += 1

            contract_num = row.get('contract_number', '').strip()

            # Deduplication by contract number
            if contract_num:
                if contract_num in seen_contracts:
                    validation_results['duplicates_removed'] += 1
                    continue  # Skip duplicate
                else:
                    seen_contracts[contract_num] = idx

            # Validate source URL
            source_url = row.get('source_url', '').strip()
            if not source_url:
                validation_results['empty_source_urls'] += 1
                validation_results['invalid_urls'].append({
                    'row': idx,
                    'contract': contract_num,
                    'issue': 'EMPTY_URL'
                })
            elif not is_valid_url(source_url):
                validation_results['malformed_urls'] += 1
                validation_results['invalid_urls'].append({
                    'row': idx,
                    'contract': contract_num,
                    'issue': 'MALFORMED_URL',
                    'url': source_url
                })

            # Validate critical fields
            critical_issues = validate_critical_fields(row)
            if critical_issues:
                validation_results['missing_critical_fields'].append({
                    'row': idx,
                    'contract': contract_num,
                    'issues': critical_issues
                })

            # PII check
            pii_violations = check_pii(row)
            if pii_violations:
                validation_results['pii_violations'].append({
                    'row': idx,
                    'contract': contract_num,
                    'violations': pii_violations
                })
                # Exclude PII rows from the clean dataset (mirror TTB validator).
                # clean.csv must NOT contain rows flagged as PII violations,
                # otherwise a downstream ship step would publish flagged PII in a
                # paid product. The violation is still reported above for review.
                continue

            # Add to clean dataset (PII rows have been excluded above)
            clean_rows.append(row)

    validation_results['deduped_rows'] = len(clean_rows)

    # Write clean CSV
    print(f"💾 Writing clean dataset: {clean_csv}")
    with open(clean_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(clean_rows)

    # Generate validation report
    print("\n" + "="*70)
    print("📊 VALIDATION SUMMARY")
    print("="*70)

    print(f"\n✅ Deduplication:")
    print(f"   • Total rows processed: {validation_results['total_rows']:,}")
    print(f"   • Unique awards (clean): {validation_results['deduped_rows']:,}")
    print(f"   • Duplicates removed: {validation_results['duplicates_removed']:,}")

    print(f"\n🔗 Source URL Validation:")
    print(f"   • Empty URLs: {validation_results['empty_source_urls']}")
    print(f"   • Malformed URLs: {validation_results['malformed_urls']}")
    print(f"   • Total URL issues: {len(validation_results['invalid_urls'])}")

    if validation_results['invalid_urls'][:5]:  # Show first 5
        print(f"\n   First 5 URL issues:")
        for issue in validation_results['invalid_urls'][:5]:
            print(f"      Row {issue['row']}: {issue['issue']} (Contract: {issue.get('contract', 'N/A')})")

    print(f"\n📋 Critical Field Validation:")
    print(f"   • Missing company names: {validation_results['null_company_names']}")
    print(f"   • Missing award amounts: {validation_results['null_award_amounts']}")
    print(f"   • Missing agencies: {validation_results['null_agencies']}")
    print(f"   • Total critical field issues: {len(validation_results['missing_critical_fields'])}")

    if validation_results['missing_critical_fields'][:5]:
        print(f"\n   First 5 critical field issues:")
        for issue in validation_results['missing_critical_fields'][:5]:
            print(f"      Row {issue['row']}: {', '.join(issue['issues'])} (Contract: {issue.get('contract', 'N/A')})")

    print(f"\n🔒 PII Scan:")
    print(f"   • Rows with PII violations: {len(validation_results['pii_violations'])}")

    if validation_results['pii_violations']:
        print(f"\n   ⚠️  PII VIOLATIONS DETECTED:")
        for violation in validation_results['pii_violations'][:10]:  # Show first 10
            print(f"      Row {violation['row']}: {', '.join(violation['violations'])} (Contract: {violation.get('contract', 'N/A')})")

    # Compare with data-engineer's report
    print(f"\n📈 Row Count Verification:")
    expected_count = 17_957  # From HARVEST_NOTES.md
    print(f"   • Expected (per harvest notes): {expected_count:,}")
    print(f"   • Actual (after deduplication): {validation_results['deduped_rows']:,}")

    discrepancy = validation_results['deduped_rows'] - expected_count
    if discrepancy != 0:
        print(f"   • ⚠️  DISCREPANCY: {abs(discrepancy):,} {'more' if discrepancy > 0 else 'fewer'} than expected")
        print(f"   • This represents {abs(discrepancy)/expected_count*100:.1f}% difference")
    else:
        print(f"   • ✅ Perfect match!")

    # Final verdict
    print("\n" + "="*70)
    has_critical_blockers = (
        validation_results['null_company_names'] > 0 or
        validation_results['null_award_amounts'] > 0 or
        validation_results['null_agencies'] > 0
    )

    has_pii_findings = len(validation_results['pii_violations']) > 0

    if has_critical_blockers:
        print("❌ VALIDATION FAILED: Critical data quality issues")
        print("   → Missing required fields prevent shipping")
        print("   → DO NOT PROCEED to compliance")
        return 1
    elif has_pii_findings:
        print("⚠️  VALIDATION COMPLETE WITH FINDINGS")
        print(f"   → {len(validation_results['pii_violations'])} rows contained potential PII — REMOVED from clean dataset")
        print(f"   → Clean dataset (PII-excluded) written to: {clean_csv}")
        print(f"   → {validation_results['deduped_rows']:,} unique awards ready")
        print("\n   📋 NEXT STEPS:")
        print("      1. Forward to compliance-officer for final review")
        print(f"      2. {len(validation_results['pii_violations'])} flagged rows are excluded from clean.csv pending compliance decision")
        return 0
    else:
        print("✅ VALIDATION PASSED: Dataset clean and ready")
        print(f"   → Clean dataset written to: {clean_csv}")
        print(f"   → {validation_results['deduped_rows']:,} unique awards ready")
        print("   → Forward to compliance-officer for final review")
        return 0

if __name__ == '__main__':
    exit(main())
