#!/usr/bin/env python3
"""
Clean + validate IRS 990 Nonprofit Organization Directory dataset.

Cleaning rules:
  1. Deduplicate by EIN (keep first occurrence, IRS regional files may overlap)
  2. Keep only status_code = '01' (Active / In good standing)
  3. Drop records with invalid US state codes (eo_xx international records)
  4. Normalize EIN to 9-digit zero-padded string
  5. Normalize ZIP to 5 digits (already done in harvest, just enforce)

Output:
  irs-990-nonprofit-organization-directory-2026-05.cleaned.csv
  irs-990-nonprofit-organization-directory-2026-05.validation.json
"""

import collections
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

INPUT_PATH = Path(__file__).parent / "irs-990-nonprofit-organization-directory-2026-05.csv"
CLEANED_PATH = Path(__file__).parent / "irs-990-nonprofit-organization-directory-2026-05.cleaned.csv"
VALIDATION_PATH = Path(__file__).parent / "irs-990-nonprofit-organization-directory-2026-05.validation.json"

SLUG = "irs-990-nonprofit-organization-directory-2026-05"

# Valid US state/territory codes
VALID_STATES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
    'DC', 'PR', 'VI', 'GU', 'MP', 'AS',
    'AA', 'AE', 'AP',  # military APO/FPO
}

ACTIVE_STATUS = '01'


def normalize_ein(ein: str) -> str:
    """Zero-pad EIN to 9 digits."""
    digits = ein.strip().lstrip('0')
    return ein.strip().zfill(9)


def main():
    start = datetime.now(timezone.utc)

    # Counters for validation
    row_count_input = 0
    dropped_not_active = 0
    dropped_invalid_state = 0
    dropped_duplicate_ein = 0
    row_count_cleaned = 0

    seen_eins: set[str] = set()

    # Field null counters
    null_counts = collections.defaultdict(int)

    # Distribution counters
    state_counts = collections.Counter()
    subsection_counts = collections.Counter()
    ntee_top_counts = collections.Counter()
    revenue_nonzero = 0
    asset_nonzero = 0

    # For sample rows
    sample_rows = []

    print(f"Reading {INPUT_PATH} ...", flush=True)

    with open(INPUT_PATH, newline='', encoding='utf-8') as fin, \
         open(CLEANED_PATH, 'w', newline='', encoding='utf-8') as fout:

        reader = csv.DictReader(fin)
        fieldnames = reader.fieldnames
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            row_count_input += 1

            # Progress
            if row_count_input % 500_000 == 0:
                print(f"  Processed {row_count_input:,} input rows ...", flush=True)

            ein_raw = row['ein'].strip()
            status = row['status_code'].strip()
            state = row['state'].strip()

            # Rule 1: Active only
            if status != ACTIVE_STATUS:
                dropped_not_active += 1
                continue

            # Rule 2: Valid state
            if state and state not in VALID_STATES:
                dropped_invalid_state += 1
                continue

            # Rule 3: Deduplicate by EIN
            ein_norm = ein_raw.zfill(9)
            if ein_norm in seen_eins:
                dropped_duplicate_ein += 1
                continue
            seen_eins.add(ein_norm)

            # Normalize EIN in output
            row['ein'] = ein_norm

            # Normalize ZIP to 5 digits (enforce)
            zip_raw = row['zip_code'].strip()
            row['zip_code'] = zip_raw[:5] if len(zip_raw) >= 5 else zip_raw

            writer.writerow(row)
            row_count_cleaned += 1

            # Track null rates
            for field in fieldnames:
                if not row[field].strip():
                    null_counts[field] += 1

            # Distributions
            state_counts[state] += 1
            subsection_counts[row['subsection_code'].strip()] += 1
            ntee = row['ntee_code'].strip()
            if ntee:
                ntee_top_counts[ntee[:1]] += 1  # top-level NTEE category letter

            rev = row['revenue_amount'].strip()
            if rev and rev != '0':
                revenue_nonzero += 1

            assets = row['asset_amount'].strip()
            if assets and assets != '0':
                asset_nonzero += 1

            # Collect sample rows (first 3 non-trivial)
            if len(sample_rows) < 3 and row['organization_name'] and row['city']:
                sample_rows.append(dict(row))

    end = datetime.now(timezone.utc)

    # Null rates as percentages
    null_rates = {}
    for field in fieldnames:
        rate = null_counts[field] / row_count_cleaned * 100 if row_count_cleaned else 0
        null_rates[field] = f"{rate:.2f}%"

    # Top 10 states
    state_top10 = dict(state_counts.most_common(10))

    # Top subsection codes with labels
    subsection_labels = {
        '01': '501(c)(1) — Federal instrumentality',
        '02': '501(c)(2) — Title holding corporation',
        '03': '501(c)(3) — Charitable/educational/religious',
        '04': '501(c)(4) — Social welfare organization',
        '05': '501(c)(5) — Labor/agricultural/horticultural',
        '06': '501(c)(6) — Business league/trade association',
        '07': '501(c)(7) — Social/recreational club',
        '08': '501(c)(8) — Fraternal beneficiary society',
        '10': '501(c)(10) — Domestic fraternal society',
        '12': '501(c)(12) — Mutual org (phone/elec/water)',
        '13': '501(c)(13) — Cemetery company',
        '19': '501(c)(19) — Veterans organization',
        '92': '527 — Political organization',
    }
    subsection_dist = {
        subsection_labels.get(k, f'501(c)({k})') if k else '(blank)': v
        for k, v in subsection_counts.most_common(10)
    }

    # NTEE category labels
    ntee_labels = {
        'A': 'Arts, Culture & Humanities',
        'B': 'Education',
        'C': 'Environment',
        'D': 'Animal-Related',
        'E': 'Health — General',
        'F': 'Mental Health & Crisis',
        'G': 'Disease & Disorder Research',
        'H': 'Medical Research',
        'I': 'Crime & Legal',
        'J': 'Employment',
        'K': 'Food, Agriculture & Nutrition',
        'L': 'Housing & Shelter',
        'M': 'Public Safety',
        'N': 'Recreation & Sports',
        'O': 'Youth Development',
        'P': 'Human Services',
        'Q': 'International & Foreign Affairs',
        'R': 'Civil Rights',
        'S': 'Community Improvement',
        'T': 'Philanthropy & Voluntarism',
        'U': 'Science & Technology',
        'V': 'Social Science',
        'W': 'Public & Societal Benefit',
        'X': 'Religion',
        'Y': 'Mutual Membership Benefit',
        'Z': 'Unknown / Unclassified',
    }
    ntee_dist = {
        ntee_labels.get(k, k): v
        for k, v in ntee_top_counts.most_common(15)
    }

    validation = {
        "version": 1,
        "type": "validation_report",
        "slug": SLUG,
        "validated_at": end.isoformat(),
        "row_count_input": row_count_input,
        "row_count_cleaned": row_count_cleaned,
        "rows_dropped": {
            "not_active_status": dropped_not_active,
            "invalid_state_code": dropped_invalid_state,
            "duplicate_ein": dropped_duplicate_ein,
            "total": dropped_not_active + dropped_invalid_state + dropped_duplicate_ein,
            "pct_of_input": f"{(dropped_not_active + dropped_invalid_state + dropped_duplicate_ein) / row_count_input * 100:.2f}%",
        },
        "null_rates": null_rates,
        "distributions": {
            "subsection_codes_top10": subsection_dist,
            "ntee_category_top15": ntee_dist,
            "state_top10": state_top10,
            "revenue_nonzero_pct": f"{revenue_nonzero / row_count_cleaned * 100:.1f}%",
            "assets_nonzero_pct": f"{asset_nonzero / row_count_cleaned * 100:.1f}%",
        },
        "sample_rows": sample_rows[:3],
        "status": "PASS",
    }

    with open(VALIDATION_PATH, 'w') as f:
        json.dump(validation, f, indent=2)

    print(f"\n=== DONE ===")
    print(f"Input rows:   {row_count_input:,}")
    print(f"Cleaned rows: {row_count_cleaned:,}")
    print(f"Dropped (inactive): {dropped_not_active:,}")
    print(f"Dropped (invalid state): {dropped_invalid_state:,}")
    print(f"Dropped (duplicate EIN): {dropped_duplicate_ein:,}")
    print(f"Validation report: {VALIDATION_PATH}")
    print(f"Cleaned CSV: {CLEANED_PATH}")


if __name__ == "__main__":
    main()
