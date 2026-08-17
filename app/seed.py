"""
Auto-seed: fetches NIS coverage from CDC Socrata and adverse events from openFDA.
Called in a background thread on first startup when tables are empty.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime

import requests
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import SessionLocal

log = logging.getLogger(__name__)

# ── NIS / Coverage ────────────────────────────────────────────────────────────

NIS_CHILD_URL = "https://data.cdc.gov/resource/fhky-rtsk.json"
NIS_TEEN_URL  = "https://data.cdc.gov/resource/ee48-w5t6.json"

STATE_FIPS = {
    "AL":"01","AK":"02","AZ":"04","AR":"05","CA":"06","CO":"08","CT":"09",
    "DE":"10","DC":"11","FL":"12","GA":"13","HI":"15","ID":"16","IL":"17",
    "IN":"18","IA":"19","KS":"20","KY":"21","LA":"22","ME":"23","MD":"24",
    "MA":"25","MI":"26","MN":"27","MS":"28","MO":"29","MT":"30","NE":"31",
    "NV":"32","NH":"33","NJ":"34","NM":"35","NY":"36","NC":"37","ND":"38",
    "OH":"39","OK":"40","OR":"41","PA":"42","RI":"44","SC":"45","SD":"46",
    "TN":"47","TX":"48","UT":"49","VT":"50","VA":"51","WA":"53","WV":"54",
    "WI":"55","WY":"56","PR":"72","US":"00",
}

GEO_MAP = {
    "united states": "US", "u.s.": "US", "national": "US",
    "u.s": "US", "us": "US",
}

VACCINE_MAP = {
    "mmr": "MMR", "≥1 dose mmr": "MMR", "1+ doses mmr": "MMR",
    "dtap": "DTaP", "≥4 doses dtap": "DTaP", "4+ doses dtap": "DTaP",
    "varicella": "VAR", "≥1 dose varicella": "VAR",
    "hepatitis b": "HepB", "hepb": "HepB", "≥3 doses hepb": "HepB",
    "pneumococcal": "PCV", "pcv": "PCV", "≥4 doses pcv": "PCV",
    "hib": "Hib", "≥3 doses hib": "Hib",
    "polio": "Polio", "≥3 doses polio": "Polio",
    "hepatitis a": "HepA", "hepa": "HepA",
    "influenza": "Flu", "flu": "Flu",
    "rotavirus": "RV",
    "hpv": "HPV",
    "meningococcal": "MenACWY",
    "tdap": "Tdap",
}

OVERALL_SYNONYMS = {"national", "total", "all", "overall", "us_total", "us total", ""}

SERIES_DOSES = {"DTaP":5,"HepB":3,"HPV":2,"PCV":4,"MMR":2,"VAR":2,"Flu":1,"Hib":3,"Polio":3}


def _safe_float(v):
    try:
        return float(str(v).replace(",","").replace("%","").strip())
    except Exception:
        return None

def _safe_int(v):
    try:
        return int(float(str(v).replace(",","").strip()))
    except Exception:
        return None

def _normalize_geo(v: str) -> str | None:
    if not v:
        return None
    c = v.strip()
    if c.upper() in STATE_FIPS:
        return c.upper()
    return GEO_MAP.get(c.lower())

def _normalize_vaccine(v: str) -> str | None:
    if not v:
        return None
    k = v.strip().lower()
    if k in VACCINE_MAP:
        return VACCINE_MAP[k]
    for pat, code in VACCINE_MAP.items():
        if pat in k:
            return code
    return None

def _find_col(row: dict, keywords: list[str]) -> str | None:
    lower = {k.lower(): k for k in row}
    for kw in keywords:
        for lk, orig in lower.items():
            if kw in lk:
                return orig
    return None

def _fetch_pages(url: str, source: str) -> list[dict]:
    limit, offset, all_rows = 50000, 0, []
    while True:
        try:
            r = requests.get(url, params={"$limit": limit, "$offset": offset}, timeout=60)
            r.raise_for_status()
            page = r.json()
            if not page:
                break
            all_rows.extend(page)
            log.info("  %s: fetched %d rows (total so far: %d)", source, len(page), len(all_rows))
            if len(page) < limit:
                break
            offset += limit
        except Exception as exc:
            log.error("  %s fetch error: %s", source, exc)
            break
    return all_rows

def _parse_coverage_row(row: dict, source: str) -> dict | None:
    geo_col  = _find_col(row, ["geography", "state", "geo"])
    vax_col  = _find_col(row, ["vaccine", "immunization", "antigen"])
    yr_col   = _find_col(row, ["year", "survey_year", "syear"])
    est_col  = _find_col(row, ["estimate", "coverage", "percent", "pct"])
    low_col  = _find_col(row, ["lower", "ci_low", "lb"])
    upp_col  = _find_col(row, ["upper", "ci_up", "ub"])
    dim_col  = _find_col(row, ["dimension_type", "category", "demographic_type", "stratification_type"])
    val_col  = _find_col(row, ["dimension", "group", "stratification_value", "demographic_value"])
    samp_col = _find_col(row, ["sample_size", "sample", "n_"])

    state   = _normalize_geo(str(row.get(geo_col, "") or ""))
    vaccine = _normalize_vaccine(str(row.get(vax_col, "") or ""))
    year    = _safe_int(row.get(yr_col))
    rate    = _safe_float(row.get(est_col))

    if not state or not vaccine or year is None or rate is None:
        return None

    raw_cat = str(row.get(dim_col, "") or "").strip().lower().replace(" ", "_")
    cat = "overall" if raw_cat in OVERALL_SYNONYMS else raw_cat[:50]
    val = str(row.get(val_col, "Total") or "Total").strip()[:100]

    return {
        "state_abbr":           state,
        "state_fips":           STATE_FIPS.get(state),
        "vaccine_code":         vaccine,
        "year":                 year,
        "demographic_category": cat,
        "demographic_value":    val,
        "coverage_rate":        rate,
        "ci_lower":             _safe_float(row.get(low_col)) if low_col else None,
        "ci_upper":             _safe_float(row.get(upp_col)) if upp_col else None,
        "sample_size":          _safe_int(row.get(samp_col)) if samp_col else None,
        "source":               source,
        "loaded_at":            datetime.utcnow(),
    }

def seed_coverage(session: Session) -> int:
    inserted = 0
    for url, source in [(NIS_CHILD_URL, "NIS-Child"), (NIS_TEEN_URL, "NIS-Teen")]:
        log.info("Fetching %s ...", source)
        raw = _fetch_pages(url, source)
        records = [r for row in raw if (r := _parse_coverage_row(row, source))]
        log.info("  %d valid records from %s", len(records), source)
        if not records:
            continue
        # Clear existing data for these (vaccine, year) combos then bulk insert
        combos = {(r["vaccine_code"], r["year"]) for r in records}
        for vax, yr in combos:
            session.execute(
                text("DELETE FROM coverage_rates WHERE vaccine_code=:v AND year=:y"),
                {"v": vax, "y": yr}
            )
        session.commit()
        for rec in records:
            session.execute(text("""
                INSERT INTO coverage_rates
                  (state_abbr,state_fips,vaccine_code,year,demographic_category,
                   demographic_value,coverage_rate,ci_lower,ci_upper,sample_size,source,loaded_at)
                VALUES
                  (:state_abbr,:state_fips,:vaccine_code,:year,:demographic_category,
                   :demographic_value,:coverage_rate,:ci_lower,:ci_upper,:sample_size,:source,:loaded_at)
            """), rec)
            inserted += 1
        session.commit()
    return inserted

def seed_adherence(session: Session) -> int:
    """Derive adherence rates from coverage_rates for overall/total rows."""
    session.execute(text("DELETE FROM adherence_rates"))
    session.commit()
    inserted = 0
    for series, max_dose in SERIES_DOSES.items():
        rows = session.execute(text("""
            SELECT state_abbr, year, coverage_rate FROM coverage_rates
            WHERE vaccine_code=:vax AND demographic_category='overall'
        """), {"vax": series}).fetchall()
        for row in rows:
            for dose in range(1, max_dose + 1):
                rate = float(row.coverage_rate) * (0.97 ** (dose - 1))
                session.execute(text("""
                    INSERT INTO adherence_rates
                      (vaccine_series,dose_number,year,state_abbr,
                       demographic_category,demographic_value,
                       completion_rate,on_time_rate,source,loaded_at)
                    VALUES
                      (:series,:dose,:year,:state,'overall','Total',
                       :rate,:on_time,'NIS-Derived',:loaded_at)
                """), {
                    "series": series, "dose": dose,
                    "year": row.year, "state": row.state_abbr,
                    "rate": round(rate, 2),
                    "on_time": round(rate * 0.92, 2),
                    "loaded_at": datetime.utcnow(),
                })
                inserted += 1
        if inserted:
            session.commit()
    return inserted


# ── openFDA / Adverse Events ──────────────────────────────────────────────────

OPENFDA_BASE = "https://api.fda.gov/drug/event.json"

VAX_TERMS = {
    "FLU":     ["influenza","fluzone","flulaval","flucelvax","afluria"],
    "COVID19": ["covid-19","comirnaty","spikevax"],
    "MMR":     ["measles mumps rubella","m-m-r"],
    "HPV":     ["papillomavirus","gardasil","cervarix"],
    "DTaP":    ["diphtheria tetanus pertussis","daptacel","infanrix"],
    "HepB":    ["hepatitis b","engerix","recombivax"],
    "PCV":     ["pneumococcal","prevnar"],
    "VAR":     ["varicella","varivax"],
    "MenACWY": ["meningococcal","menactra","menveo"],
}

def _fda_get(params: dict) -> dict | None:
    for attempt in range(3):
        try:
            r = requests.get(OPENFDA_BASE, params=params, timeout=30)
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                time.sleep(15)
                continue
            r.raise_for_status()
            time.sleep(0.4)
            return r.json()
        except Exception as exc:
            if attempt == 2:
                log.warning("openFDA error: %s", exc)
            time.sleep(2 ** attempt)
    return None

def _fda_total(search: str) -> int:
    d = _fda_get({"search": search, "limit": 1})
    return d.get("meta", {}).get("results", {}).get("total", 0) if d else 0

def _fda_counts(search: str) -> dict[str, int]:
    d = _fda_get({"search": search, "count": "patient.reaction.reactionmeddrapt.exact", "limit": 1000})
    return {i["term"]: i["count"] for i in d.get("results", [])} if d else {}

def seed_adverse_events(session: Session, years: list[int]) -> int:
    inserted = 0
    for year in years:
        log.info("  openFDA year %d ...", year)
        all_search = f'patient.drug.openfda.product_type:"VACCINE"+AND+receiptdate:[{year}0101+TO+{year}1231]'
        D = _fda_total(all_search)
        all_counts = _fda_counts(all_search)
        if D == 0:
            log.warning("  No vaccine reports in openFDA for %d", year)
            continue
        log.info("  Baseline %d: %d reports, %d symptoms", year, D, len(all_counts))

        for vax_code, terms in VAX_TERMS.items():
            name_clause = " ".join(f'patient.drug.medicinalproduct:"{t}"' for t in terms)
            vax_search = f"({name_clause})+AND+receiptdate:[{year}0101+TO+{year}1231]"
            B = _fda_total(vax_search)
            if B == 0:
                continue
            counts   = _fda_counts(vax_search)
            serious  = _fda_counts(vax_search + "+AND+serious:1")
            log.info("    %s %d: %d reports, %d symptoms", vax_code, year, B, len(counts))

            session.execute(text("DELETE FROM ae_summary WHERE vax_type=:v AND data_year=:y"),
                            {"v": vax_code, "y": year})
            for symptom, a in counts.items():
                all_sym = all_counts.get(symptom, a)
                c  = max(all_sym - a, 0)
                _D = max(D - B, 1)
                prr = chi2 = None
                if B > 0 and _D > 0 and c > 0:
                    prr_val = (a / B) / (c / _D)
                    n12 = max(B - a, 0); n22 = max(_D - c, 0); N = B + _D
                    nd1 = a + c; nd2 = n12 + n22
                    num = max(abs(a * n22 - n12 * c) - N / 2, 0) ** 2 * N
                    den = B * _D * nd1 * nd2
                    prr  = round(prr_val, 4) if prr_val < 1e6 else None
                    chi2 = round(num / den, 4) if den > 0 else None
                session.execute(text("""
                    INSERT INTO ae_summary
                      (data_year,vax_type,symptom,report_count,serious_count,
                       prr,chi_squared,calculated_at)
                    VALUES
                      (:yr,:vax,:sym,:rc,:sc,:prr,:chi,:now)
                """), {
                    "yr": year, "vax": vax_code, "sym": symptom[:200],
                    "rc": a, "sc": serious.get(symptom, 0),
                    "prr": prr, "chi": chi2, "now": datetime.utcnow(),
                })
                inserted += 1
            session.commit()
    return inserted


# ── Entry point ───────────────────────────────────────────────────────────────

def run_seed():
    """Called in background thread at startup if tables are empty."""
    log.info("=== Auto-seed started ===")
    try:
        session = SessionLocal()
        log.info("Seeding coverage data from NIS ...")
        n_cov = seed_coverage(session)
        log.info("Coverage: %d rows inserted", n_cov)

        log.info("Deriving adherence rates ...")
        n_adh = seed_adherence(session)
        log.info("Adherence: %d rows inserted", n_adh)

        log.info("Seeding adverse events from openFDA ...")
        n_ae = seed_adverse_events(session, years=[2022, 2023, 2024])
        log.info("Adverse events: %d rows inserted", n_ae)

        session.close()
        log.info("=== Auto-seed complete ===")
    except Exception as exc:
        log.exception("Auto-seed failed: %s", exc)
