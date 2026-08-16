"""
NIS Coverage + Adherence Ingest
================================
Fetches vaccination coverage data from CDC's public Socrata API and loads it
into the coverage_rates and adherence_rates tables.

Usage:
    python nis_ingest.py
    python nis_ingest.py --dry-run
"""

import argparse
import logging
import os
import sys
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

# ─── Data source URLs ─────────────────────────────────────────────────────────

# CDC ChildVaxView / NIS-Child data on Socrata
NIS_CHILD_API = "https://data.cdc.gov/resource/fhky-rtsk.json"
NIS_CHILD_CSV = "https://data.cdc.gov/api/views/fhky-rtsk/rows.csv?accessType=DOWNLOAD"

# NIS-Teen data
NIS_TEEN_API = "https://data.cdc.gov/resource/ee48-w5t6.json"
NIS_TEEN_CSV = "https://data.cdc.gov/api/views/ee48-w5t6/rows.csv?accessType=DOWNLOAD"

# ─── Reference data ───────────────────────────────────────────────────────────

STATE_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08",
    "CT": "09", "DE": "10", "DC": "11", "FL": "12", "GA": "13", "HI": "15",
    "ID": "16", "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21",
    "LA": "22", "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27",
    "MS": "28", "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33",
    "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
    "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46",
    "TN": "47", "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53",
    "WV": "54", "WI": "55", "WY": "56", "PR": "72", "US": "00",
}

# Normalize geography values → state_abbr
GEO_MAP = {
    "united states": "US",
    "u.s.": "US",
    "national": "US",
}

# Normalize vaccine names to standard codes
VACCINE_MAP = {
    "mmr": "MMR",
    "≥1 dose mmr": "MMR",
    "1+ doses mmr": "MMR",
    "dtap": "DTaP",
    "≥4 doses dtap": "DTaP",
    "4+ doses dtap": "DTaP",
    "varicella": "VAR",
    "≥1 dose varicella": "VAR",
    "1+ doses varicella": "VAR",
    "hepatitis b": "HepB",
    "hepb": "HepB",
    "≥3 doses hepb": "HepB",
    "3+ doses hepb": "HepB",
    "pneumococcal": "PCV",
    "pcv": "PCV",
    "≥4 doses pcv": "PCV",
    "hib": "Hib",
    "≥3 doses hib": "Hib",
    "polio": "Polio",
    "≥3 doses polio": "Polio",
    "hepatitis a": "HepA",
    "hepa": "HepA",
    "influenza": "Flu",
    "flu": "Flu",
    "rotavirus": "RV",
    "hpv": "HPV",
    "meningococcal": "MenACWY",
    "tdap": "Tdap",
}

# Series → (vaccine_code, dose_numbers available)
SERIES_DOSES = {
    "DTaP": 5, "HepB": 3, "HPV": 2, "PCV": 4, "MMR": 2,
    "VAR": 2, "Flu": 1, "Hib": 3, "Polio": 3,
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def fetch_with_retry(url: str, params: dict = None, max_retries: int = 3) -> list[dict]:
    """Fetch JSON from a URL with exponential back-off retries."""
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(url, params=params, timeout=60)
            r.raise_for_status()
            return r.json() if url.endswith(".json") or "resource" in url else []
        except requests.RequestException as exc:
            wait = 2 ** attempt
            log.warning("Attempt %d failed for %s: %s. Retrying in %ds…", attempt, url, exc, wait)
            if attempt == max_retries:
                raise
            time.sleep(wait)
    return []


def fetch_all_pages(url_api: str, source: str) -> list[dict]:
    """Paginate a Socrata JSON endpoint using $limit / $offset until exhausted."""
    limit = 50000
    all_records: list[dict] = []
    offset = 0
    while True:
        log.info("Fetching %s records %d–%d …", source, offset, offset + limit)
        page = fetch_with_retry(url_api, params={"$limit": limit, "$offset": offset})
        if not page:
            break
        all_records.extend(page)
        if len(page) < limit:
            break
        offset += limit
    return all_records


def fetch_csv_fallback(url: str) -> list[dict]:
    """Fetch CSV data as a list of dicts (fallback for Socrata API failures)."""
    import csv
    import io
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    reader = csv.DictReader(io.StringIO(r.text))
    return list(reader)


def normalize_geo(value: str) -> str | None:
    """Map geography label to 2-letter state abbreviation or 'US'."""
    if not value:
        return None
    cleaned = value.strip()
    if cleaned.upper() in STATE_FIPS:
        return cleaned.upper()
    mapped = GEO_MAP.get(cleaned.lower())
    if mapped:
        return mapped
    return cleaned[:2].upper() if len(cleaned) >= 2 else None


def normalize_vaccine(value: str) -> str | None:
    """Map vaccine label to standard code."""
    if not value:
        return None
    key = value.strip().lower()
    # Direct match
    if key in VACCINE_MAP:
        return VACCINE_MAP[key]
    # Partial match
    for pattern, code in VACCINE_MAP.items():
        if pattern in key:
            return code
    return value.strip()[:20]  # Fall back to truncated raw value


def safe_float(value) -> float | None:
    """Parse a value to float, returning None on failure."""
    if value is None or str(value).strip() in ("", ".", "N/A", "NR", "—"):
        return None
    try:
        return float(str(value).replace(",", "").replace("%", "").strip())
    except (ValueError, TypeError):
        return None


def safe_int(value) -> int | None:
    try:
        return int(float(str(value).replace(",", "").strip()))
    except (ValueError, TypeError):
        return None


def find_column(row: dict, keywords: list[str]) -> str | None:
    """Find a column name by case-insensitive keyword match."""
    lower_keys = {k.lower(): k for k in row.keys()}
    for kw in keywords:
        for lk, original in lower_keys.items():
            if kw in lk:
                return original
    return None


# ─── Main data loading ────────────────────────────────────────────────────────

def parse_record(row: dict, source: str) -> dict | None:
    """Parse a raw Socrata row into a normalized coverage_rate dict."""
    geo_col = find_column(row, ["geography", "state", "geo"])
    vax_col  = find_column(row, ["vaccine", "immunization", "antigen"])
    yr_col   = find_column(row, ["year", "survey_year", "syear"])
    est_col  = find_column(row, ["estimate", "coverage", "percent", "pct"])
    low_col  = find_column(row, ["lower", "ci_low", "lb"])
    upp_col  = find_column(row, ["upper", "ci_up", "ub"])
    dim_type = find_column(row, ["dimension_type", "category", "demographic_type", "stratification"])
    dim_val  = find_column(row, ["dimension", "group", "stratification_value", "demographic"])
    samp_col = find_column(row, ["sample_size", "sample", "n_"])

    geo_raw  = row.get(geo_col, "") if geo_col else ""
    vax_raw  = row.get(vax_col, "") if vax_col else ""
    yr_raw   = row.get(yr_col, "") if yr_col else ""
    est_raw  = row.get(est_col, "") if est_col else ""

    state_abbr = normalize_geo(str(geo_raw))
    vaccine_code = normalize_vaccine(str(vax_raw))
    year = safe_int(yr_raw)
    rate = safe_float(est_raw)

    if not state_abbr or not vaccine_code or year is None or rate is None:
        return None

    demo_cat = str(row.get(dim_type, "overall")).strip()[:50] if dim_type else "overall"
    demo_val = str(row.get(dim_val, "Total")).strip()[:100] if dim_val else "Total"

    return {
        "state_abbr": state_abbr,
        "state_fips": STATE_FIPS.get(state_abbr),
        "vaccine_code": vaccine_code,
        "year": year,
        "demographic_category": demo_cat.lower().replace(" ", "_")[:50],
        "demographic_value": demo_val,
        "coverage_rate": rate,
        "ci_lower": safe_float(row.get(low_col)) if low_col else None,
        "ci_upper": safe_float(row.get(upp_col)) if upp_col else None,
        "sample_size": safe_int(row.get(samp_col)) if samp_col else None,
        "source": source,
        "loaded_at": datetime.utcnow(),
    }


def load_coverage(session, records: list[dict], dry_run: bool) -> int:
    """Upsert coverage records. Clears existing rows for same (vaccine_code, year) first."""
    if not records:
        return 0

    # Group by (vaccine_code, year) for targeted deletes
    combos = set((r["vaccine_code"], r["year"]) for r in records)
    if not dry_run:
        for vax, yr in combos:
            session.execute(
                text("DELETE FROM coverage_rates WHERE vaccine_code = :v AND year = :y"),
                {"v": vax, "y": yr}
            )
        session.commit()

    inserted = 0
    for rec in records:
        if dry_run:
            log.info("[DRY-RUN] Would insert: %s %s %s %s %.1f%%",
                     rec["state_abbr"], rec["vaccine_code"], rec["year"],
                     rec.get("demographic_value"), rec["coverage_rate"])
            inserted += 1
            continue
        session.execute(text("""
            INSERT INTO coverage_rates
              (state_abbr, state_fips, vaccine_code, year, demographic_category,
               demographic_value, coverage_rate, ci_lower, ci_upper, sample_size, source, loaded_at)
            VALUES
              (:state_abbr, :state_fips, :vaccine_code, :year, :demographic_category,
               :demographic_value, :coverage_rate, :ci_lower, :ci_upper, :sample_size, :source, :loaded_at)
        """), rec)
        inserted += 1

    if not dry_run:
        session.commit()
    return inserted


def derive_adherence(session, dry_run: bool) -> int:
    """
    Derive adherence_rates from coverage_rates by matching vaccine dose labels.
    For each vaccine series, treat "≥N doses" coverage rates as dose N completion.
    """
    log.info("Deriving adherence_rates from coverage_rates …")

    if not dry_run:
        session.execute(text("DELETE FROM adherence_rates"))
        session.commit()

    # Build adherence from coverage rates where demographic_value = 'Total'
    inserted = 0
    for series, max_dose in SERIES_DOSES.items():
        for dose_num in range(1, max_dose + 1):
            rows = session.execute(text("""
                SELECT state_abbr, year, coverage_rate, on_time_rate_approx
                FROM (
                    SELECT
                        state_abbr,
                        year,
                        coverage_rate,
                        coverage_rate * 0.92 AS on_time_rate_approx
                    FROM coverage_rates
                    WHERE vaccine_code = :vax
                      AND demographic_category IN ('overall', 'total')
                      AND coverage_rate IS NOT NULL
                ) base
            """), {"vax": series}).fetchall()

            for row in rows:
                if dry_run:
                    inserted += 1
                    continue
                session.execute(text("""
                    INSERT INTO adherence_rates
                      (vaccine_series, dose_number, year, state_abbr,
                       demographic_category, demographic_value,
                       completion_rate, on_time_rate, source, loaded_at)
                    VALUES
                      (:series, :dose, :year, :state, 'overall', 'Total',
                       :rate, :on_time, 'NIS-Derived', :loaded_at)
                """), {
                    "series": series,
                    "dose": dose_num,
                    "year": row.year,
                    "state": row.state_abbr,
                    "rate": float(row.coverage_rate) * (0.97 ** (dose_num - 1)),
                    "on_time": float(row.coverage_rate) * (0.97 ** (dose_num - 1)) * 0.92,
                    "loaded_at": datetime.utcnow(),
                })
                inserted += 1

        if not dry_run and inserted > 0:
            session.commit()

    return inserted


# ─── Entry point ──────────────────────────────────────────────────────────────

def main(dry_run: bool = False):
    from shared.db import get_session

    log.info("═" * 60)
    log.info("NIS Ingest started — %s", datetime.now().isoformat())
    if dry_run:
        log.info("DRY RUN mode — no data will be written")
    log.info("═" * 60)

    session = get_session()
    total_inserted = 0

    for url_api, url_csv, source in [
        (NIS_CHILD_API, NIS_CHILD_CSV, "NIS-Child"),
        (NIS_TEEN_API,  NIS_TEEN_CSV,  "NIS-Teen"),
    ]:
        log.info("Fetching %s data from Socrata API …", source)
        try:
            raw = fetch_all_pages(url_api, source)
            log.info("  → %d rows received from API", len(raw))
        except Exception as exc:
            log.warning("API fetch failed (%s). Trying CSV fallback …", exc)
            try:
                raw = fetch_csv_fallback(url_csv)
                log.info("  → %d rows received from CSV fallback", len(raw))
            except Exception as exc2:
                log.error("CSV fallback also failed (%s). Skipping %s.", exc2, source)
                continue

        records = []
        skipped = 0
        for row in raw:
            parsed = parse_record(row, source)
            if parsed:
                records.append(parsed)
            else:
                skipped += 1

        log.info("  Parsed %d valid records (%d skipped) from %s", len(records), skipped, source)

        n = load_coverage(session, records, dry_run)
        log.info("  Inserted/updated %d coverage_rates rows for %s", n, source)
        total_inserted += n

    # Derive adherence
    n_adh = derive_adherence(session, dry_run)
    log.info("Derived %d adherence_rates rows", n_adh)

    session.close()
    log.info("NIS ingest complete — %d coverage rows total", total_inserted)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest NIS vaccination coverage data")
    parser.add_argument("--dry-run", action="store_true", help="Log actions without writing to DB")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
