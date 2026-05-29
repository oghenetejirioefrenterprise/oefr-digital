"""
CPA License Registry Harvester
Systematically collects CPA license data from all 50 states + DC

Requirements:
- Full name, license number, license status, issue date, expiration date
- Firm name/affiliation, city, state, license type
- Source URL for every row
"""

import json
import csv
import requests
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import time
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('harvest.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class CPALicense:
    """Standardized CPA license record"""
    full_name: str
    license_number: str
    license_status: str
    issue_date: Optional[str]
    expiration_date: Optional[str]
    firm_name: Optional[str]
    city: Optional[str]
    state: str
    license_type: str
    source_url: str

    def to_dict(self) -> Dict:
        return asdict(self)


class StateHarvester:
    """Base class for state-specific harvesters"""

    def __init__(self, state_code: str, state_name: str):
        self.state_code = state_code
        self.state_name = state_name
        self.records: List[CPALicense] = []

    def harvest(self) -> List[CPALicense]:
        """Override this method in subclasses"""
        raise NotImplementedError

    def save_records(self, output_dir: Path):
        """Save harvested records to state-specific file"""
        output_file = output_dir / f"{self.state_code.lower()}_raw.csv"

        if not self.records:
            logger.warning(f"{self.state_code}: No records to save")
            return

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'full_name', 'license_number', 'license_status',
                'issue_date', 'expiration_date', 'firm_name',
                'city', 'state', 'license_type', 'source_url'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for record in self.records:
                writer.writerow(record.to_dict())

        logger.info(f"{self.state_code}: Saved {len(self.records)} records to {output_file}")


class WashingtonHarvester(StateHarvester):
    """Washington State - Open Data Portal"""

    def __init__(self):
        super().__init__("WA", "Washington")
        self.base_url = "https://data.wa.gov/resource/pqu3-uhwj.json"

    def harvest(self) -> List[CPALicense]:
        """Fetch from Washington's open data API"""
        logger.info(f"{self.state_code}: Starting harvest from open data portal")

        offset = 0
        limit = 1000
        total_fetched = 0

        while True:
            try:
                params = {
                    "$limit": limit,
                    "$offset": offset,
                    "$order": ":id"
                }

                response = requests.get(self.base_url, params=params, timeout=30)
                response.raise_for_status()

                data = response.json()

                if not data:
                    break

                for item in data:
                    record = self._parse_record(item)
                    if record:
                        self.records.append(record)

                total_fetched += len(data)
                logger.info(f"{self.state_code}: Fetched {total_fetched} records...")

                if len(data) < limit:
                    break

                offset += limit
                time.sleep(0.5)  # Rate limiting

            except Exception as e:
                logger.error(f"{self.state_code}: Error fetching data: {e}")
                break

        logger.info(f"{self.state_code}: Harvest complete - {len(self.records)} records")
        return self.records

    def _parse_record(self, item: Dict) -> Optional[CPALicense]:
        """Parse Washington state record format"""
        try:
            # Adjust field names based on actual API response
            return CPALicense(
                full_name=f"{item.get('first_name', '')} {item.get('last_name', '')}".strip(),
                license_number=item.get('license_number', ''),
                license_status=item.get('license_status', item.get('status', '')),
                issue_date=item.get('issue_date', item.get('original_issue_date', '')),
                expiration_date=item.get('expiration_date', item.get('expiry_date', '')),
                firm_name=item.get('firm_name', item.get('employer', '')),
                city=item.get('city', ''),
                state='WA',
                license_type=item.get('license_type', 'CPA'),
                source_url=f"{self.base_url}?license_number={item.get('license_number', '')}"
            )
        except Exception as e:
            logger.warning(f"{self.state_code}: Error parsing record: {e}")
            return None


class GenericSearchHarvester(StateHarvester):
    """Generic harvester for states with search interfaces"""

    def __init__(self, state_code: str, state_name: str, search_url: str):
        super().__init__(state_code, state_name)
        self.search_url = search_url

    def harvest(self) -> List[CPALicense]:
        """Placeholder - needs state-specific implementation"""
        logger.warning(f"{self.state_code}: Generic search harvester not yet implemented")
        logger.info(f"{self.state_code}: Search URL: {self.search_url}")
        return []


def load_state_boards() -> List[Dict]:
    """Load state board configuration"""
    boards_file = Path(__file__).parent / "state_boards.json"
    with open(boards_file, 'r') as f:
        data = json.load(f)
    return data['jurisdictions']


def create_harvester(state_info: Dict) -> Optional[StateHarvester]:
    """Factory function to create appropriate harvester for each state"""
    state_code = state_info['code']
    state_name = state_info['name']
    data_access = state_info.get('data_access_type', '')

    if state_code == 'WA' and data_access == 'open_data':
        return WashingtonHarvester()
    elif data_access == 'search_only':
        return GenericSearchHarvester(state_code, state_name, state_info.get('search_url', ''))
    else:
        # Needs manual configuration
        logger.info(f"{state_code}: No harvester configured yet")
        return None


def consolidate_records(output_dir: Path):
    """Consolidate all state files into raw.csv"""
    logger.info("Consolidating all state records...")

    all_records = []
    state_files = list(output_dir.glob("*_raw.csv"))

    for state_file in state_files:
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                records = list(reader)
                all_records.extend(records)
                logger.info(f"Loaded {len(records)} records from {state_file.name}")
        except Exception as e:
            logger.error(f"Error reading {state_file}: {e}")

    # Deduplicate by license_number + state
    seen = set()
    deduplicated = []

    for record in all_records:
        key = (record['license_number'], record['state'])
        if key not in seen:
            seen.add(key)
            deduplicated.append(record)

    logger.info(f"Deduplication: {len(all_records)} → {len(deduplicated)} records")

    # Write consolidated file
    output_file = output_dir / "raw.csv"
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'full_name', 'license_number', 'license_status',
            'issue_date', 'expiration_date', 'firm_name',
            'city', 'state', 'license_type', 'source_url'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(deduplicated)

    logger.info(f"Consolidated {len(deduplicated)} records to {output_file}")
    return len(deduplicated)


def main():
    """Main harvesting pipeline"""
    logger.info("=== CPA License Registry Harvest Started ===")

    output_dir = Path(__file__).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load all state boards
    state_boards = load_state_boards()
    logger.info(f"Loaded {len(state_boards)} jurisdictions")

    # Harvest from each state
    harvest_count = 0
    for state_info in state_boards:
        state_code = state_info['code']

        harvester = create_harvester(state_info)
        if not harvester:
            continue

        try:
            logger.info(f"\n--- {state_code}: {state_info['name']} ---")
            harvester.harvest()
            harvester.save_records(output_dir)
            harvest_count += len(harvester.records)
        except Exception as e:
            logger.error(f"{state_code}: Harvest failed: {e}")

    logger.info(f"\n=== Individual harvests complete: {harvest_count} total records ===")

    # Consolidate all records
    total_records = consolidate_records(output_dir)

    logger.info(f"\n=== HARVEST COMPLETE ===")
    logger.info(f"Total records collected: {total_records}")
    logger.info(f"Target: 750,000 records")
    logger.info(f"Progress: {total_records / 750000 * 100:.1f}%")


if __name__ == "__main__":
    main()
