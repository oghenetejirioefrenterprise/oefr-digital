#!/usr/bin/env python3
"""Temporary Reddit distribution sweep — 2026-05-09"""
import asyncio
import os
import sys
from pathlib import Path

BASE = Path("/home/oghenetejiri/apps/dataStructured")
sys.path.insert(0, str(BASE))

from scripts.lib.distribution_log import already_posted, append_entry
from scripts.social_helpers import _reddit_post_browseruse, _log_entry

ITEMS = [
    {
        "item_id": "new-fmcsa-carrier-leads-2026-05-2026-05-04",
        "slug": "new-fmcsa-carrier-leads-2026-05",
        "subreddit": "Truckers",
        "title": "15,770 new FMCSA carrier registrations from DOT public data this month — compiled to CSV",
        "body": """Every month the FMCSA publishes new carrier registration data as part of their public records. I've been compiling this into clean CSVs for B2B sales teams who need to prospect new carriers.

This month: 15,770 new carriers who just registered with the FMCSA — the newest operators in the system.

Each record: carrier name, MC#, DOT#, phone, address, equipment type.

Useful for trucking insurance agents, ELD vendors, freight factoring companies, and owner-operator dispatch services who want to reach carriers before they're fully established.

Dataset is $39 as a one-time CSV download: https://buy.stripe.com/cNi14g4CP7aT8mT1iC7IY0c

Also on Gumroad: https://3563705146415.gumroad.com/l/bvdnbx

Happy to answer questions about what's in the data.""",
    },
    {
        "item_id": "new-business-formations-csv-2026-05-2026-05-05",
        "slug": "new-business-formations-csv-2026-05",
        "subreddit": "smallbusiness",
        "title": "15,997 new Florida LLC and corporation filings from state records this month — compiled to CSV",
        "body": """Florida Division of Corporations publishes all new business filings as public records. I've been compiling these into clean CSVs monthly.

This month: 15,997 new LLCs and corps filed in Florida.

Includes: business name, registered agent, address, entity type (LLC/Corp), filing date.

Useful for insurance agents targeting new businesses, bookkeepers and CPAs prospecting new clients, web designers, registered agent firms, payroll processors, and business banking reps.

New businesses are prime prospects — they have not established vendor relationships yet.

$49 as a one-time CSV: https://buy.stripe.com/aFaaEQc5h66Pbz5f9s7IY0f""",
    },
    {
        "item_id": "samgov-small-biz-contractor-leads-2026-05-2026-05-05",
        "slug": "samgov-small-biz-contractor-leads-2026-05",
        "subreddit": "govcontracting",
        "title": "4,731 SAM.gov small-business IT contractors in the DC/MD/VA corridor — compiled from public data",
        "body": """SAM.gov registration data is public. I have been compiling it into targeted datasets for people working in federal contracting.

This batch covers 4,731 small-business IT contractors in the DMV corridor registered in SAM.gov — categorized by set-aside type: 8(a), HUBZone, WOSB, SDVOSB, and SB.

Includes: company name, DUNS, cage code, address, set-aside types, NAICS codes, point of contact.

Useful for:
- Primes looking for teaming partners by set-aside type
- IT staffing agencies targeting federal contractors as clients
- SaaS vendors (proposal software, compliance tools, timekeeping) selling into the fed IT market

$49 one-time CSV: https://buy.stripe.com/dRm5kwb1dfHp7iPe5o7IY0g""",
    },
    {
        "item_id": "fl-real-estate-agent-licenses-2026-05-2026-05-06",
        "slug": "fl-real-estate-agent-licenses-2026-05",
        "subreddit": "RealEstate",
        "title": "319,247 Florida licensed real estate agents and brokers from DBPR public records — compiled to CSV",
        "body": """Florida DBPR publishes all active real estate licenses as public records. I compiled these into a clean, searchable CSV.

Current count: 319,247 active licensed agents and brokers in Florida.

Each record: name, license type (Sales Associate/Broker), license number, license status, address, associated brokerage.

Useful for:
- Real estate SaaS companies prospecting FL agents (Follow Up Boss, Lofty, kvCORE SDRs)
- Mortgage lenders building agent referral networks
- Title insurance companies
- E&O insurance brokers
- CE providers selling continuing education credits to agents

$49 one-time CSV: https://buy.stripe.com/cNi8wIb1dfHpeLhe5o7IY0k""",
    },
    {
        "item_id": "cms-medicare-home-health-agencies-2026-05-2026-05-05",
        "slug": "cms-medicare-home-health-agencies-2026-05",
        "subreddit": "homehealth",
        "title": "12,392 Medicare-certified home health agencies across the US — compiled from CMS public data",
        "body": """CMS publishes a complete list of Medicare-certified providers as public data. I compiled all home health agencies into a clean CSV.

Current count: 12,392 Medicare-certified home health agencies across 55 US states and territories.

Each record: agency name, address, phone, CMS certification number, certification date, state.

Useful for:
- Medical SaaS vendors (EVV software, scheduling, billing, CRM for home health operators)
- DME and wound-care supply reps
- Healthcare staffing agencies
- Insurance brokers selling liability and workers comp to HHAs

$49 one-time CSV: https://buy.stripe.com/5kQcMYfhtgLtdHdgdw7IY0h""",
    },
    {
        "item_id": "faa-civil-aircraft-registration-2026-05-2026-05-06",
        "slug": "faa-civil-aircraft-registration-2026-05",
        "subreddit": "aviation",
        "title": "302,810 US-registered civil aircraft from the FAA Releasable Aircraft Database — compiled to CSV",
        "body": """The FAA releases its complete aircraft registration database as public data quarterly. I compiled it into a clean, searchable CSV.

Current count: 302,810 active US-registered civil aircraft.

Each record: N-number, serial number, make, model, aircraft type (fixed-wing/rotorcraft/glider/etc), engine type, year manufactured, registrant name, address, registrant type (Individual/LLC/Corporation/Government).

Useful for:
- Aviation insurance brokers prospecting aircraft owners
- Avionics shops targeting ADS-B upgrade prospects by aircraft age and type
- MRO facilities and aircraft parts vendors prospecting by make/model
- Flight training schools identifying local aircraft types
- Aviation SaaS vendors

$69 one-time CSV: https://buy.stripe.com/5kQdR20mz0Mvbz5f9s7IY0l""",
    },
    {
        "item_id": "fl-alcoholic-beverage-licensees-2026-05-2026-05-07",
        "slug": "fl-alcoholic-beverage-licensees-2026-05",
        "subreddit": "bartenders",
        "title": "52,152 active Florida alcohol licensees from DBPR — bars, restaurants, package stores compiled to CSV",
        "body": """Florida DBPR publishes all active alcohol licenses as public records. I compiled these into a clean CSV.

Current count: 52,152 active licensed establishments in Florida.

Includes: license type (on-premise/off-premise/vendor), business name, address, county, license number, issue and expiration dates.

Types covered: bars, restaurants, nightclubs, hotels with bars, package stores, beer/wine shops, distributors, manufacturers.

Useful for: liquor distributors prospecting on-premise accounts, POS vendors (Toast, Square, SpotOn) targeting FL hospitality, payment processors, linen/supply companies, music licensing reps, insurance brokers selling liquor liability.

$49 one-time CSV: https://buy.stripe.com/cNi5kwglx9j10Ur0ey7IY0m""",
    },
    {
        "item_id": "nppes-physical-therapist-clinics-2026-05-2026-05-07",
        "slug": "nppes-physical-therapist-clinics-2026-05",
        "subreddit": "physicaltherapy",
        "title": "377,805 active US physical therapists from CMS NPPES — full national database compiled to CSV",
        "body": """CMS NPPES (the National Provider Identifier database) is fully public. I compiled all physical therapists and PT clinics into a searchable CSV.

Current count: 377,805 active licensed PTs and PT practices, all 50 states.

Each record: NPI, provider name, credentials (DPT/PT/MPT/etc), taxonomy/specialty, practice address, phone number, state license number.

Phone coverage: 99.98% of records have a phone number.

This kind of data is useful for medical SaaS vendors (EMR, scheduling, billing software for PT practices), medical equipment reps, healthcare staffing agencies, CE providers, and liability insurance brokers who need a full national prospecting list.

$79 one-time CSV: https://buy.stripe.com/6oU3co9X9br9dHd2mG7IY0n""",
    },
    {
        "item_id": "tx-tdlr-electricians-2026-05-2026-05-07",
        "slug": "tx-tdlr-electricians-2026-05",
        "subreddit": "electricians",
        "title": "204,535 licensed Texas electricians from TDLR — master, journeyman, contractors compiled to CSV",
        "body": """TDLR (Texas Dept. of Licensing and Regulation) publishes all active electrical licenses as public records. I compiled these into a clean CSV.

Current count: 204,535 active licensed electricians in Texas.

License classes included:
- Master Electricians
- Journeyman Electricians
- Electrical Contractors (companies)
- Apprentice Electricians
- Residential Wiremen
- Sign Electricians

Each record: name, license class, license number, business address, city, ZIP, phone, expiration date.

This is useful for electrical supply distributors (Graybar, Rexel, Anixter), field service SaaS SDRs (ServiceTitan, Jobber, Procore targeting electrical contractors), OSHA training providers, CE education companies, and insurance brokers.

$59 one-time CSV: https://buy.stripe.com/00w28k3yLbr946D5yS7IY0o""",
    },
    {
        "item_id": "tx-tdlr-hvac-contractors-2026-05-2026-05-07",
        "slug": "tx-tdlr-hvac-contractors-2026-05",
        "subreddit": "HVAC",
        "title": "56,001 active Texas HVAC contractors and AC technicians from TDLR — full TX market compiled to CSV",
        "body": """TDLR publishes all active HVAC licenses as public records. I compiled these into a clean CSV.

Current count: 56,001 active HVAC license holders in Texas.

License types:
- A/C Contractors (companies)
- A/C Technicians
- Service Technicians

Each record: name, license type, license number, business address, city, ZIP, phone, expiration date.

Useful for: Carrier/Trane/Lennox dealer territory reps, ServiceTitan/FieldEdge SDRs targeting HVAC companies, refrigerant suppliers, HVAC CE education providers, and insurance brokers selling liability and workers comp to HVAC companies.

$49 one-time CSV: https://buy.stripe.com/8x27sEglx3YHdHd8L47IY0p""",
    },
    {
        "item_id": "ca-cslb-licensed-contractors-2026-05-2026-05-07",
        "slug": "ca-cslb-licensed-contractors-2026-05",
        "subreddit": "Construction",
        "title": "232,617 active California licensed contractors from CSLB — 30+ trade classes in one CSV",
        "body": """CSLB (California Contractors State License Board) publishes all active contractor licenses as public records. I compiled these into a clean, searchable CSV.

Current count: 232,617 active licensed contractors in California.

Major trade classes:
- Class B (General Building): 75,100+
- Class A (General Engineering): 15,000+
- C10 Electrical: 18,000+
- C36 Plumbing: 11,000+
- C20 HVAC/Heating: 7,000+
- C39 Roofing, C33 Painting, C27 Landscaping + 25 more specialty trades

Each record: name, license class, address, city, county, ZIP, phone, expiration date. 99.9% phone coverage.

Useful for: Procore/Buildertrend SDRs, construction insurance and bonding brokers, building material and equipment distributors, safety/OSHA training companies, lien management software vendors, subcontractor-focused SaaS.

$79 one-time CSV: https://buy.stripe.com/4gMaEQb1deDlcD91iC7IY0q""",
    },
    {
        "item_id": "nppes-dentists-dental-practices-2026-05-2026-05-07",
        "slug": "nppes-dentists-dental-practices-2026-05",
        "subreddit": "Dentistry",
        "title": "371,786 active US dentists and dental practices from CMS NPPES — full national database compiled to CSV",
        "body": """CMS NPPES (National Provider Identifier database) is fully public. I compiled all dentists and dental practices into a searchable CSV.

Current count: 371,786 active dental providers, all 50 states.

Specialties included:
- General Dentists: 173,000+
- Orthodontists: 15,000+
- Oral and Maxillofacial Surgeons: 12,000+
- Endodontists: 9,100+
- Periodontists: 4,300+
- Pediatric Dentists: 8,300+
- Prosthodontists, Pathologists, Radiologists

Each record: NPI, name, specialty, practice address, city, state, ZIP, phone. 100% phone coverage.

This is useful for dental supply companies (Patterson, Henry Schein, Benco), dental SaaS SDRs (Dentrix, Eaglesoft, Carestream), dental lab companies, dental CE education providers, dental insurance brokers, and staffing agencies.

$79 one-time: https://buy.stripe.com/cNi9AM3yL0MvfPl0ey7IY0r""",
    },
    {
        "item_id": "sec-registered-investment-advisers-2026-05-2026-05-07",
        "slug": "sec-registered-investment-advisers-2026-05",
        "subreddit": "FinancialPlanning",
        "title": "16,551 SEC-registered investment adviser firms from IAPD public data — compiled to CSV",
        "body": """The SEC IAPD (Investment Adviser Public Disclosure) database is fully public. I compiled all registered RIA firms into a clean CSV.

Current count: 16,551 active SEC-registered investment adviser firms.

Each record: firm name, CRD number, SEC number, registration date, status, business address, state.

Useful for:
- Wealthtech SaaS companies (portfolio management, CRM, compliance tools) prospecting new RIA clients
- Asset manager and ETF sponsor BD teams targeting RIA gatekeepers
- Third-party recruiters targeting breakaway adviser talent
- Boutique M&A advisers tracking RIA consolidation activity
- Teams currently paying $5K-20K/yr for enterprise platforms that wrap this same free SEC public data

$79 one-time CSV: https://buy.stripe.com/bJe00c1qD7aT8mT0ey7IY0s""",
    },
]


def main():
    username = os.environ.get("REDDIT_USERNAME", "")
    password = os.environ.get("REDDIT_PASSWORD", "")
    if not username or not password:
        print("ERROR: REDDIT_USERNAME / REDDIT_PASSWORD not set — run: source ~/.profile", file=sys.stderr)
        sys.exit(1)

    results = []
    for item in ITEMS:
        item_id = item["item_id"]
        slug = item["slug"]
        subreddit = item["subreddit"]
        title = item["title"]
        body = item["body"]
        channel = f"reddit:r/{subreddit}"

        if already_posted(BASE, item_id, channel):
            print(f"SKIP — {item_id} already posted to {channel}")
            results.append({"item_id": item_id, "channel": channel, "status": "skipped"})
            continue

        print(f"\nPosting: {item_id} -> r/{subreddit}")
        print(f"  Title: {title[:60]}...")

        try:
            post_url = asyncio.run(
                _reddit_post_browseruse(subreddit, title, body, username, password)
            )
            append_entry(BASE, _log_entry(
                item_id=item_id,
                slug=slug,
                channel=channel,
                status="posted",
                url=post_url,
                content=f"{title}\n\n{body}",
            ))
            print(f"  POSTED — {post_url}")
            results.append({"item_id": item_id, "channel": channel, "status": "posted", "url": post_url})
        except Exception as exc:
            err = str(exc)
            append_entry(BASE, _log_entry(
                item_id=item_id,
                slug=slug,
                channel=channel,
                status="failed",
                error=err,
            ))
            print(f"  FAILED — {err[:120]}", file=sys.stderr)
            results.append({"item_id": item_id, "channel": channel, "status": "failed", "error": err[:120]})

    print("\n=== REDDIT SWEEP SUMMARY ===")
    posted = [r for r in results if r["status"] == "posted"]
    failed = [r for r in results if r["status"] == "failed"]
    skipped = [r for r in results if r["status"] == "skipped"]
    print(f"Posted:  {len(posted)}")
    print(f"Failed:  {len(failed)}")
    print(f"Skipped: {len(skipped)}")
    for r in posted:
        print(f"  OK  {r['item_id']} -> {r['channel']} — {r.get('url', '')}")
    for r in failed:
        print(f"  ERR {r['item_id']} -> {r['channel']} — {r.get('error', '')}")


if __name__ == "__main__":
    main()
