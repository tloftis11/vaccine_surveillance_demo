"""
Adverse Event Ingest — openFDA API
====================================
Replaces the VAERS ZIP download approach with FDA's public openFDA REST API,
which serves the same underlying VAERS data without file downloads.

API docs: https://open.fda.gov/apis/drug/event/

Usage:
    python vaers_ingest.py
    python vaers_ingest.py --years 2022,2023
    python vaers_ingest.py --dry-run
"""

import argparse
import logging
import os
import time
from datetime import datetime

import requests
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── openFDA ──────────────────────────────────────────────────────────────────

OPENFDA_BASE = "https://api.fda.gov/drug/event.json"

# Maps our internal vaccine codes to openFDA medicinalproduct search terms.
# Quoted phrases use Lucene exact-phrase matching.
VAX_TERMS: dict[str, list[str]] = {
    "FLU":      ["influenza", "fluzone", "flulaval", "flucelvax", "afluria"],
    "COVID19":  ["covid-19", "comirnaty", "spikevax", "janssen covid"],
    "MMR":      ["measles mumps rubella", "mmr", "m-m-r"],
    "HPV":      ["papillomavirus", "gardasil", "cervarix"],
    "DTaP":     ["diphtheria tetanus pertussis", "daptacel", "infanrix", "pediarix"],
    "HepB":     ["hepatitis b", "engerix", "recombivax"],
    "PCV":      ["pneumococcal", "prevnar"],
    "VAR":      ["varicella", "varivax"],
    "MenACWY":  ["meningococcal", "menactra", "menveo"],
    "Tdap":     ["tetanus diphtheria pertussis", "adacel", "boostrix"],
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get(params: dict, retries: int = 3) -> dict | None:
    """GET openFDA with retry and rate-limit respect."""
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(OPENFDA_BASE, params=params, timeout=30)
            if r.status_code == 404:
                return None  # no matching records
            if r.status_code == 429:
                wait = 10 * attempt
                log.warning("Rate limited — waiting %ds", wait)
                time.sleep(wait)
                continue
            r.raise_for_status()
            time.sleep(0.3)  # stay well under 240 req/min limit
            return r.json()
        except requests.RequestException as exc:
            if attempt == retries:
                log.error("openFDA request failed: %s", exc)
                return None
            time.sleep(2 ** attempt)
    return None


def get_total(search: str) -> int:
    """Return total number of reports matching a search query."""
    data = _get({"search": search, "limit": 1})
    if not data:
        return 0
    return data.get("meta", {}).get("results", {}).get("total", 0)


def get_reaction_counts(search: str) -> dict[str, int]:
    """Return {symptom: count} for the top 1000 reactions matching search."""
    data = _get({
        "search": search,
        "count": "patient.reaction.reactionmeddrapt.exact",
        "limit": 1000,
    })
    if not data:
        return {}
    return {item["term"]: item["count"] for item in data.get("results", [])}


def build_vax_search(vax_code: str, year: int) -> str:
    """Build an openFDA search string for a vaccine type and year."""
    terms = VAX_TERMS.get(vax_code, [])
    if not terms:
        return ""
    name_clause = " ".join(f'patient.drug.medicinalproduct:"{t}"' for t in terms)
    year_clause = f"receiptdate:[{year}0101+TO+{year}1231]"
    return f"({name_clause})+AND+{year_clause}"


# ─── Core pipeline ────────────────────────────────────────────────────────────

def compute_signals(session, year: int, dry_run: bool) -> int:
    """
    Query openFDA for each vaccine type, compute PRR + chi-squared, and
    upsert into ae_summary. Returns number of rows written.
    """
    log.info("  Fetching 'all vaccines' baseline for %d …", year)
    all_search = f"patient.drug.openfda.product_type:\"VACCINE\"+AND+receiptdate:[{year}0101+TO+{year}1231]"
    D = get_total(all_search)
    all_counts = get_reaction_counts(all_search)

    if D == 0:
        log.warning("  No vaccine reports found in openFDA for %d — skipping", year)
        return 0

    log.info("  Baseline: %d total vaccine reports, %d distinct symptoms", D, len(all_counts))

    rows_written = 0

    for vax_code in VAX_TERMS:
        vax_search = build_vax_search(vax_code, year)
        if not vax_search:
            continue

        B = get_total(vax_search)
        if B == 0:
            log.info("    %s %d: no reports", vax_code, year)
            continue

        reaction_counts = get_reaction_counts(vax_search)
        serious_counts = get_reaction_counts(vax_search + "+AND+serious:1")

        log.info("    %s %d: %d reports, %d symptoms", vax_code, year, B, len(reaction_counts))

        records = []
        for symptom, a in reaction_counts.items():
            all_sym = all_counts.get(symptom, a)
            c = max(all_sym - a, 0)   # other-vaccine reports with this symptom
            _D = max(D - B, 1)        # total other-vaccine reports

            prr = None
            chi2 = None
            if B > 0 and _D > 0 and c > 0:
                prr_val = (a / B) / (c / _D)
                # Yates-corrected chi-squared on the 2x2 contingency table
                n12 = max(B - a, 0)
                n22 = max(_D - c, 0)
                N   = B + _D
                n_dot1 = a + c
                n_dot2 = n12 + n22
                num = max(abs(a * n22 - n12 * c) - N / 2, 0) ** 2 * N
                den = B * _D * n_dot1 * n_dot2
                prr = round(prr_val, 4) if prr_val < 1e6 else None
                chi2 = round(num / den, 4) if den > 0 else None

            records.append({
                "data_year":     year,
                "vax_type":      vax_code,
                "symptom":       symptom[:200],
                "report_count":  a,
                "serious_count": serious_counts.get(symptom, 0),
                "prr":           prr,
                "chi_squared":   chi2,
                "calculated_at": datetime.utcnow(),
            })

        if dry_run:
            log.info("    [DRY-RUN] Would write %d ae_summary rows for %s %d", len(records), vax_code, year)
            rows_written += len(records)
            continue

        if records:
            session.execute(text("""
                DELETE FROM ae_summary
                WHERE vax_type = :vax AND data_year = :yr
            """), {"vax": vax_code, "yr": year})

            session.execute(text("""
                INSERT INTO ae_summary
                  (data_year, vax_type, symptom, report_count, serious_count,
                   prr, chi_squared, calculated_at)
                VALUES
                  (:data_year, :vax_type, :symptom, :report_count, :serious_count,
                   :prr, :chi_squared, :calculated_at)
            """), records)
            session.commit()
            rows_written += len(records)
            log.info("    Wrote %d rows", len(records))

    return rows_written


# ─── Entry point ──────────────────────────────────────────────────────────────

def main(years: list[int], dry_run: bool = False):
    from shared.db import get_session

    log.info("=" * 60)
    log.info("openFDA Adverse Event Ingest — %s", datetime.now().isoformat())
    log.info("Years: %s", years)
    if dry_run:
        log.info("DRY RUN — no data will be written")
    log.info("=" * 60)

    session = get_session()
    total = 0

    for year in years:
        log.info("Processing year %d …", year)
        n = compute_signals(session, year, dry_run)
        log.info("Year %d complete — %d rows", year, n)
        total += n

    session.close()
    log.info("Ingest complete — %d total ae_summary rows", total)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest vaccine adverse events via openFDA")
    parser.add_argument("--years", default="2020,2021,2022,2023,2024",
                        help="Comma-separated list of years (default: 2020-2024)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    year_list = [int(y.strip()) for y in args.years.split(",")]
    main(years=year_list, dry_run=args.dry_run)
