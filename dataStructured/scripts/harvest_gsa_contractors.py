#!/usr/bin/env python3
"""
GSA Schedule Contract Holders Data Harvester

Scrapes public GSA eLibrary data to create a comprehensive directory
of all active GSA Schedule (Multiple Award Schedule) contract holders.

Data source: https://www.gsaelibrary.gsa.gov/
Data rights: Public domain per FAR 9.105-2(b)(1)
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
import os
from datetime import datetime
import re
from urllib.parse import urljoin, parse_qs, urlparse
import sys

class GSAContractorHarvester:
    def __init__(self):
        self.base_url = "https://www.gsaelibrary.gsa.gov/ElibMain"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })
        self.contractors = []
        self.errors = []

    def fetch_contractor_list(self, letter):
        """Fetch list of contractors starting with given letter"""
        url = f"{self.base_url}/contractorList.do"
        params = {"scheduleNumber": "", "letterPressed": letter}

        try:
            response = self.session.get(url, params=params, timeout=30)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                contractor_links = soup.find_all('a', href=re.compile(r'contractorInfo\.do'))

                contractors_data = []
                for link in contractor_links:
                    href = link.get('href')
                    # Parse contract number and name from URL
                    if 'contractNumber=' in href and 'contractorName=' in href:
                        parsed = urlparse(href)
                        params = parse_qs(parsed.query)

                        contractor = {
                            'contractor_name': link.text.strip(),
                            'contract_number': params.get('contractNumber', [''])[0],
                            'detail_url': urljoin(self.base_url + '/', href)
                        }
                        contractors_data.append(contractor)

                return contractors_data
            else:
                self.errors.append({
                    'letter': letter,
                    'error': f'HTTP {response.status_code}',
                    'stage': 'list_fetch'
                })
                return []

        except Exception as e:
            self.errors.append({
                'letter': letter,
                'error': str(e),
                'stage': 'list_fetch'
            })
            return []

    def fetch_contractor_details(self, contractor_data):
        """Fetch detailed information for a contractor"""
        try:
            response = self.session.get(contractor_data['detail_url'], timeout=30)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract details from the page
            details = contractor_data.copy()

            # Helper function to extract data from table rows
            def extract_field(label_pattern):
                """Extract value from a table row where the label matches the pattern"""
                label_elem = soup.find(string=re.compile(label_pattern, re.I))
                if label_elem:
                    # Find the parent row, then get the next <td> sibling
                    parent_row = label_elem.find_parent('tr')
                    if parent_row:
                        tds = parent_row.find_all('td')
                        if len(tds) >= 2:
                            return tds[1].get_text(strip=True, separator=' ')
                return None

            # Extract SAM UEI
            uei = extract_field(r'SAM UEI|Unique Entity ID|UEI')
            if uei:
                details['uei'] = uei

            # Extract CAGE code
            cage = extract_field(r'CAGE')
            if cage:
                details['cage_code'] = cage

            # Extract DUNS (legacy, but might still be present)
            duns = extract_field(r'DUNS')
            if duns:
                details['duns'] = duns

            # Extract address
            address = extract_field(r'Address')
            if address:
                details['address'] = address.replace('<BR>', ', ')

            # Extract phone
            phone = extract_field(r'Phone')
            if phone:
                details['phone'] = phone

            # Extract email
            email_elem = soup.find('a', href=re.compile(r'mailto:'))
            if email_elem:
                details['email'] = email_elem.get_text(strip=True)

            # Extract web address
            web_elem = soup.find(string=re.compile(r'Web Address', re.I))
            if web_elem:
                parent_row = web_elem.find_parent('tr')
                if parent_row:
                    link = parent_row.find('a')
                    if link:
                        details['website'] = link.get('href', '').strip()

            # Look for SINs (Special Item Numbers) in the page
            # SINs are often in a separate table or list
            sin_elem = soup.find(string=re.compile(r'SIN|Schedule', re.I))
            if sin_elem:
                parent_elem = sin_elem.find_parent('tr')
                if not parent_elem:
                    parent_elem = sin_elem.find_parent('div')
                if parent_elem:
                    details['sin_schedule'] = parent_elem.get_text(strip=True, separator=' | ')

            # Look for NAICS codes — scope the scrape to the NAICS-labeled cell
            # only. Scanning the whole page with \b\d{6}\b captured ANY 6-digit
            # run (zip+4 fragments like '902100', contract-number fragments like
            # '123456'), polluting the product column and inflating the
            # has_naics completeness metric to ~100% regardless of real data.
            naics_field = extract_field(r'NAICS')
            if naics_field:
                naics_codes = re.findall(r'\b\d{6}\b', naics_field)
                if naics_codes:
                    # Deduplicate
                    naics_codes = list(set(naics_codes))
                    details['naics_codes'] = ', '.join(sorted(naics_codes))

            # Look for business type flags
            business_types = []
            page_text = soup.get_text()
            if re.search(r'Small Business', page_text, re.I):
                business_types.append('Small Business')
            if re.search(r'8\(a\)', page_text):
                business_types.append('8(a)')
            if re.search(r'HUBZone', page_text, re.I):
                business_types.append('HUBZone')
            if re.search(r'Woman.*Owned|WOSB', page_text, re.I):
                business_types.append('WOSB')
            if re.search(r'Veteran.*Owned|VOSB', page_text, re.I):
                business_types.append('VOSB')
            if re.search(r'Service.*Disabled.*Veteran|SDVOSB', page_text, re.I):
                business_types.append('SDVOSB')

            if business_types:
                details['business_type'] = ', '.join(business_types)

            # Source URL is required
            details['source_url'] = contractor_data['detail_url']

            return details

        except Exception as e:
            self.errors.append({
                'contractor': contractor_data.get('contractor_name'),
                'error': str(e),
                'stage': 'detail_fetch'
            })
            return None

    def _flush_checkpoint(self, checkpoint_path):
        """Atomically persist everything collected so far so a crash mid-run does
        not discard hours of scraping. Writes to a temp file then os.replace()."""
        if not checkpoint_path or not self.contractors:
            return
        try:
            os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
            tmp_path = checkpoint_path + ".tmp"
            pd.DataFrame(self.contractors).to_csv(tmp_path, index=False)
            os.replace(tmp_path, checkpoint_path)
            print(f"  [checkpoint] flushed {len(self.contractors)} records → {checkpoint_path}")
        except Exception as exc:
            # A checkpoint failure must not abort the harvest itself.
            print(f"  [checkpoint] WARNING: failed to flush checkpoint: {exc}")

    def harvest_all(self, max_per_letter=None, checkpoint_path=None):
        """Harvest all contractors from A-Z and 0-9.

        If checkpoint_path is given, the accumulated results are flushed to that
        file after each letter so a crash does not lose the whole run.
        """
        letters = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ') + list('0123456789')

        print(f"Starting GSA contractor harvest at {datetime.now().isoformat()}")
        print(f"Will process {len(letters)} letter/number categories")

        total_found = 0
        total_processed = 0

        for letter in letters:
            print(f"\n{'='*60}")
            print(f"Processing letter: {letter}")
            print('='*60)

            # Fetch contractor list for this letter
            contractors_list = self.fetch_contractor_list(letter)
            total_found += len(contractors_list)

            print(f"Found {len(contractors_list)} contractors for letter '{letter}'")

            # Limit for testing if specified
            if max_per_letter:
                contractors_list = contractors_list[:max_per_letter]
                print(f"Limited to {len(contractors_list)} for testing")

            # Fetch details for each contractor
            for i, contractor_data in enumerate(contractors_list, 1):
                if i % 50 == 0:
                    print(f"  Processed {i}/{len(contractors_list)} contractors for '{letter}'...")

                details = self.fetch_contractor_details(contractor_data)
                if details:
                    self.contractors.append(details)
                    total_processed += 1

                # Rate limiting - be respectful to GSA servers
                time.sleep(0.5)  # 2 requests per second max

            print(f"Completed letter '{letter}': {len(contractors_list)} contractors")

            # Flush a crash-safe checkpoint after every letter.
            self._flush_checkpoint(checkpoint_path)

            # Pause between letters
            time.sleep(2)

        print(f"\n{'='*60}")
        print(f"Harvest complete!")
        print(f"Total found: {total_found}")
        print(f"Total processed: {total_processed}")
        print(f"Errors: {len(self.errors)}")
        print('='*60)

        return self.contractors

    def save_to_csv(self, output_file):
        """Save harvested data to CSV"""
        if not self.contractors:
            print("No contractor data to save")
            return

        df = pd.DataFrame(self.contractors)

        # Ensure source_url is present (hard requirement)
        if 'source_url' not in df.columns:
            df['source_url'] = df.apply(
                lambda row: f"{self.base_url}/contractorInfo.do?contractNumber={row.get('contract_number', '')}&contractorName={row.get('contractor_name', '')}&executeQuery=YES",
                axis=1
            )

        # Reorder columns to put key fields first
        priority_cols = ['contractor_name', 'contract_number', 'uei', 'cage_code',
                        'naics_codes', 'business_type', 'sin_schedule', 'address',
                        'contract_period', 'source_url', 'detail_url']

        existing_cols = [col for col in priority_cols if col in df.columns]
        other_cols = [col for col in df.columns if col not in priority_cols]
        ordered_cols = existing_cols + other_cols

        df = df[ordered_cols]

        # Save to CSV
        df.to_csv(output_file, index=False)
        print(f"\nSaved {len(df)} contractors to {output_file}")

        return df

    def generate_report(self, output_file, df):
        """Generate harvest report JSON"""
        report = {
            "harvest_date": datetime.now().isoformat(),
            "data_source": "GSA eLibrary (https://www.gsaelibrary.gsa.gov/)",
            "data_rights": "Public domain per FAR 9.105-2(b)(1)",
            "total_records": len(df),
            "total_errors": len(self.errors),
            "columns": df.columns.tolist(),
            "sample_records": df.head(3).to_dict('records'),
            "completeness_check": {
                "has_contractor_name": df['contractor_name'].notna().sum(),
                "has_contract_number": df['contract_number'].notna().sum(),
                "has_source_url": df['source_url'].notna().sum() if 'source_url' in df.columns else 0,
                "has_uei": df['uei'].notna().sum() if 'uei' in df.columns else 0,
                "has_naics": df['naics_codes'].notna().sum() if 'naics_codes' in df.columns else 0,
            },
            "error_count": len(self.errors),
            "errors": self.errors,  # Full list — do not truncate; a high error
                                    # rate is the signal that the run was partial.
            "status": "COMPLETE" if len(self.errors) < len(df) * 0.1 else "PARTIAL"
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Saved harvest report to {output_file}")

        return report


def main():
    harvester = GSAContractorHarvester()

    # For full harvest, set max_per_letter=None
    # For testing, use a small number like 5
    test_mode = len(sys.argv) > 1 and sys.argv[1] == '--test'
    max_per_letter = 5 if test_mode else None

    if test_mode:
        print("RUNNING IN TEST MODE (5 contractors per letter)")

    # Harvest data. Checkpoint per-letter so a crash after hours of scraping does
    # not discard the whole run (the final dataset.csv is still the canonical output).
    output_csv = "state/products/gsa-schedule-contract-holders/dataset.csv"
    checkpoint_csv = "state/products/gsa-schedule-contract-holders/dataset.checkpoint.csv"
    contractors = harvester.harvest_all(
        max_per_letter=max_per_letter, checkpoint_path=checkpoint_csv
    )

    # Save to CSV
    df = harvester.save_to_csv(output_csv)

    # Generate report
    report_file = "state/products/gsa-schedule-contract-holders/harvest-report.json"
    report = harvester.generate_report(report_file, df)

    print(f"\n✅ Harvest complete!")
    print(f"   Records: {len(df)}")
    print(f"   Errors: {len(harvester.errors)}")
    print(f"   Status: {report['status']}")


if __name__ == "__main__":
    main()
