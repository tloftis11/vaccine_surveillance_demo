"""
VAERS Ingest
=============
Downloads VAERS annual ZIP files, parses the three CSVs per year
(VAERSDATA, VAERSVAX, VAERSSYMPTOMS), loads to PostgreSQL, and
recomputes ae_summary PRR/chi-squared aggregates.

Usage:
    python vaers_ingest.py
    python vaers_ingest.py --years 2022,2023
    python vaers_ingest.py --years 2023 --data-dir /path/to/zips

VAERS manual download:
    https://vaers.hhs.gov/data/datasets.html
    Place downloaded ZIPs in pipelines/data/downloads/
    Naming convention: 2023VAERSData.zip
"""

import argparse
import io
import logging
import math
import os
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from sqlalchemy import text
from tqdm import tqdm

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── Paths ────────────────────────────────────────────────────────────────────

HERE = Path(__file__).parent
DOWNLOAD_DIR = HERE / "data" / "downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ─── VAERS download URL template ──────────────────────────────────────────────
# The actual download requires navigating their site. We try the direct URL;
# if it fails, we fall back to looking for the file in DOWNLOAD_DIR.

VAERS_URL_TEMPLATE = "https://vaers.hhs.gov/eSubDownload/data/{year}VAERSData.zip"
VAERS_URL_TEMPLATE_ALT = "https://vaers.hhs.gov/data/datasets/{year}VAERSData.zip"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://vaers.hhs.gov/data/datasets.html",
}

CHUNK_SIZE = 5_000  # rows per DB commit batch

# ─── Column mappings ──────────────────────────────────────────────────────────

DATA_BOOL_COLS = {"DIED", "L_THREAT", "HOSPITAL", "DISABLE"}

SYMPTOM_COLS = [
    ("SYMPTOM1", "SYMPTOMVERSION1"),
    ("SYMPTOM2", "SYMPTOMVERSION2"),
    ("SYMPTOM3", "SYMPTOMVERSION3"),
    ("SYMPTOM4", "SYMPTOMVERSION4"),
    ("SYMPTOM5", "SYMPTOMVERSION5"),
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def safe_bool(val) -> bool:
    if pd.isna(val):
        return False
    return str(val).strip().upper() in ("Y", "1", "TRUE", "YES")


def safe_date(val):
    if pd.isna(val) or str(val).strip() in ("", ".", "nan"):
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            return datetime.strptime(str(val).strip(), fmt).date()
        except ValueError:
            continue
    return None


def safe_float(val) -> float | None:
    try:
        v = float(val)
        return v if not math.isnan(v) else None
    except (TypeError, ValueError):
        return None


def safe_int(val) -> int | None:
    try:
        v = float(val)
        return int(v) if not math.isnan(v) else None
    except (TypeError, ValueError):
        return None


def normalize_str(val, maxlen: int = None) -> str | None:
    if pd.isna(val) or str(val).strip() in ("", "nan"):
        return None
    s = str(val).strip()
    return s[:maxlen] if maxlen else s


# ─── Download ─────────────────────────────────────────────────────────────────

def get_zip_path(year: int) -> Path | None:
    """
    Return path to the ZIP file for a given year.
    Tries downloading first, then looks in DOWNLOAD_DIR.
    """
    filename = f"{year}VAERSData.zip"
    local_path = DOWNLOAD_DIR / filename

    if local_path.exists():
        log.info("Using existing file: %s", local_path)
        return local_path

    urls = [
        VAERS_URL_TEMPLATE.format(year=year),
        VAERS_URL_TEMPLATE_ALT.format(year=year),
    ]
    for url in urls:
        log.info("Attempting download: %s", url)
        try:
            session = requests.Session()
            session.get("https://vaers.hhs.gov/data/datasets.html", headers=HEADERS, timeout=15)
            r = session.get(url, headers=HEADERS, timeout=300, stream=True)
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            with open(local_path, "wb") as f:
                with tqdm(total=total, unit="B", unit_scale=True, desc=f"Downloading {year}") as bar:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        bar.update(len(chunk))
            log.info("Downloaded to %s", local_path)
            return local_path
        except requests.RequestException as exc:
            log.warning("Download failed (%s): %s — trying next URL", url, exc)

    log.warning(
        "All download attempts failed for %d.\n"
        "  → Please download manually from https://vaers.hhs.gov/data/datasets.html\n"
        "  → Place %s in %s",
        year, filename, DOWNLOAD_DIR
    )
    return None


def read_csv_from_zip(zip_path: Path, pattern: str) -> pd.DataFrame:
    """Read the first CSV matching pattern from a ZIP archive."""
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        matches = [n for n in names if pattern.upper() in n.upper() and n.upper().endswith(".CSV")]
        if not matches:
            # Try non-domestic variant
            matches = [n for n in names if pattern.upper() in n.upper()]
        if not matches:
            log.warning("Pattern '%s' not found in %s. Contents: %s", pattern, zip_path.name, names)
            return pd.DataFrame()
        target = matches[0]
        log.info("  Reading %s from %s", target, zip_path.name)
        with zf.open(target) as f:
            return pd.read_csv(f, dtype=str, encoding="latin-1", low_memory=False)


# ─── DB loading ───────────────────────────────────────────────────────────────

def load_year(session, year: int, zip_path: Path) -> dict:
    """Parse and load all three VAERS files for one year. Returns row counts."""
    counts = {"reports": 0, "vaccines": 0, "symptoms": 0}

    # ── 1. VAERSDATA ──────────────────────────────────────────────────────────
    log.info("[%d] Reading VAERSDATA …", year)
    df_data = read_csv_from_zip(zip_path, "VAERSDATA")
    if df_data.empty:
        log.error("[%d] No VAERSDATA found — skipping year", year)
        return counts

    df_data.columns = [c.strip().upper() for c in df_data.columns]
    vaers_ids = df_data["VAERS_ID"].dropna().astype(int).tolist()

    # Delete existing rows for these IDs
    log.info("[%d] Removing existing %d report IDs …", year, len(vaers_ids))
    for i in range(0, len(vaers_ids), 1000):
        chunk_ids = vaers_ids[i:i + 1000]
        session.execute(
            text("DELETE FROM vaers_reports WHERE vaers_id = ANY(:ids)"),
            {"ids": chunk_ids}
        )
    session.commit()

    log.info("[%d] Loading %d VAERSDATA rows …", year, len(df_data))
    for i in tqdm(range(0, len(df_data), CHUNK_SIZE), desc=f"{year} reports"):
        chunk = df_data.iloc[i:i + CHUNK_SIZE]
        rows = []
        for _, row in chunk.iterrows():
            vid = safe_int(row.get("VAERS_ID"))
            if vid is None:
                continue
            died       = safe_bool(row.get("DIED"))
            l_threat   = safe_bool(row.get("L_THREAT"))
            hosp       = safe_bool(row.get("HOSPITAL"))
            disable    = safe_bool(row.get("DISABLE"))
            serious    = died or l_threat or hosp or disable

            onset_days = safe_int(row.get("NUMDAYS"))
            rows.append({
                "vaers_id":         vid,
                "received_date":    safe_date(row.get("RECVDATE")),
                "state_abbr":       normalize_str(row.get("STATE"), 2),
                "age_years":        safe_float(row.get("AGE_YRS")),
                "sex":              normalize_str(row.get("SEX"), 1),
                "died":             died,
                "life_threatening": l_threat,
                "hospitalized":     hosp,
                "hospital_days":    safe_int(row.get("HOSPDAYS")),
                "disabled":         disable,
                "recovered":        safe_bool(row.get("RECOVD")) if pd.notna(row.get("RECOVD")) else None,
                "vax_date":         safe_date(row.get("VAX_DATE")),
                "onset_date":       safe_date(row.get("ONSET_DATE")),
                "onset_days":       onset_days,
                "serious":          serious,
                "data_year":        year,
            })

        if rows:
            now = datetime.utcnow()
            for r in rows:
                r["loaded_at"] = now
            session.execute(text("""
                INSERT INTO vaers_reports
                  (vaers_id, received_date, state_abbr, age_years, sex,
                   died, life_threatening, hospitalized, hospital_days, disabled,
                   recovered, vax_date, onset_date, onset_days, serious, data_year, loaded_at)
                VALUES
                  (:vaers_id, :received_date, :state_abbr, :age_years, :sex,
                   :died, :life_threatening, :hospitalized, :hospital_days, :disabled,
                   :recovered, :vax_date, :onset_date, :onset_days, :serious, :data_year, :loaded_at)
                ON CONFLICT (vaers_id) DO NOTHING
            """), rows)
            session.commit()
            counts["reports"] += len(rows)

    # ── 2. VAERSVAX ───────────────────────────────────────────────────────────
    log.info("[%d] Reading VAERSVAX …", year)
    df_vax = read_csv_from_zip(zip_path, "VAERSVAX")
    if not df_vax.empty:
        df_vax.columns = [c.strip().upper() for c in df_vax.columns]

        # Delete existing vaccine rows for these IDs
        for i in range(0, len(vaers_ids), 1000):
            chunk_ids = vaers_ids[i:i + 1000]
            session.execute(
                text("DELETE FROM vaers_vaccines WHERE vaers_id = ANY(:ids)"),
                {"ids": chunk_ids}
            )
        session.commit()

        for i in tqdm(range(0, len(df_vax), CHUNK_SIZE), desc=f"{year} vaccines"):
            chunk = df_vax.iloc[i:i + CHUNK_SIZE]
            rows = []
            for _, row in chunk.iterrows():
                vid = safe_int(row.get("VAERS_ID"))
                if vid is None:
                    continue
                rows.append({
                    "vaers_id":        vid,
                    "vax_type":        normalize_str(row.get("VAX_TYPE"), 50),
                    "vax_manufacturer":normalize_str(row.get("VAX_MFRE"), 100),
                    "vax_dose_series": normalize_str(row.get("VAX_DOSE_SERIES"), 20),
                    "vax_route":       normalize_str(row.get("VAX_ROUTE"), 20),
                    "vax_site":        normalize_str(row.get("VAX_SITE"), 30),
                })
            if rows:
                session.execute(text("""
                    INSERT INTO vaers_vaccines
                      (vaers_id, vax_type, vax_manufacturer, vax_dose_series, vax_route, vax_site)
                    VALUES
                      (:vaers_id, :vax_type, :vax_manufacturer, :vax_dose_series, :vax_route, :vax_site)
                """), rows)
                # Note: vaers_vaccines has no loaded_at column per the schema
                session.commit()
                counts["vaccines"] += len(rows)

    # ── 3. VAERSSYMPTOMS ──────────────────────────────────────────────────────
    log.info("[%d] Reading VAERSSYMPTOMS …", year)
    df_sym = read_csv_from_zip(zip_path, "VAERSSYMPTOMS")
    if not df_sym.empty:
        df_sym.columns = [c.strip().upper() for c in df_sym.columns]

        for i in range(0, len(vaers_ids), 1000):
            chunk_ids = vaers_ids[i:i + 1000]
            session.execute(
                text("DELETE FROM vaers_symptoms WHERE vaers_id = ANY(:ids)"),
                {"ids": chunk_ids}
            )
        session.commit()

        for i in tqdm(range(0, len(df_sym), CHUNK_SIZE), desc=f"{year} symptoms"):
            chunk = df_sym.iloc[i:i + CHUNK_SIZE]
            rows = []
            for _, row in chunk.iterrows():
                vid = safe_int(row.get("VAERS_ID"))
                if vid is None:
                    continue
                for sym_col, ver_col in SYMPTOM_COLS:
                    symptom = normalize_str(row.get(sym_col), 200)
                    if symptom:
                        rows.append({
                            "vaers_id":       vid,
                            "symptom":        symptom,
                            "meddra_version": normalize_str(row.get(ver_col), 20),
                        })
            if rows:
                session.execute(text("""
                    INSERT INTO vaers_symptoms (vaers_id, symptom, meddra_version)
                    VALUES (:vaers_id, :symptom, :meddra_version)
                """), rows)
                session.commit()
                counts["symptoms"] += len(rows)

    return counts


# ─── PRR computation ──────────────────────────────────────────────────────────

def compute_ae_summary(session, years: list[int]) -> int:
    """
    Compute ae_summary for each (vax_type, symptom, year) combination.
    PRR = (a/b) / (c/d) where:
      a = reports for THIS vaccine with THIS symptom
      b = total reports for THIS vaccine
      c = reports for ALL OTHER vaccines with THIS symptom
      d = total reports for ALL OTHER vaccines
    chi_squared = (|ad - bc| - N/2)^2 * N / ((a+b)(c+d)(a+c)(b+d))
    """
    log.info("Computing ae_summary PRR/chi-squared …")

    for year in years:
        log.info("  Computing signals for year %d …", year)
        session.execute(text("DELETE FROM ae_summary WHERE data_year = :y"), {"y": year})
        session.commit()

        # Pull raw event counts via SQL
        rows = session.execute(text("""
            SELECT
                vv.vax_type,
                vs.symptom,
                COUNT(DISTINCT vr.vaers_id)                            AS a,
                SUM(CASE WHEN vr.serious THEN 1 ELSE 0 END)::int      AS serious_count
            FROM vaers_reports vr
            JOIN vaers_vaccines vv ON vr.vaers_id = vv.vaers_id
            JOIN vaers_symptoms vs ON vr.vaers_id = vs.vaers_id
            WHERE vr.data_year = :year
              AND vv.vax_type IS NOT NULL
              AND vs.symptom IS NOT NULL
            GROUP BY vv.vax_type, vs.symptom
            HAVING COUNT(DISTINCT vr.vaers_id) >= 5
        """), {"year": year}).fetchall()

        if not rows:
            log.warning("  No rows found for year %d — skipping PRR computation", year)
            continue

        # Build pandas DataFrame for vectorized PRR calculation
        df = pd.DataFrame(rows, columns=["vax_type", "symptom", "a", "serious_count"])
        df["a"] = df["a"].astype(float)

        # b: total DISTINCT reports per vax_type (queried separately to avoid
        # the symptom-aggregation overcounting that would occur if we summed `a`).
        b_rows = session.execute(text("""
            SELECT vv.vax_type, COUNT(DISTINCT vr.vaers_id) AS b
            FROM vaers_reports vr
            JOIN vaers_vaccines vv ON vr.vaers_id = vv.vaers_id
            WHERE vr.data_year = :year AND vv.vax_type IS NOT NULL
            GROUP BY vv.vax_type
        """), {"year": year}).fetchall()
        b_map = {r[0]: float(r[1]) for r in b_rows}
        df["b"] = df["vax_type"].map(b_map)

        # a+c: total DISTINCT reports per symptom (across ALL vax_types, not just those
        # that passed the a >= 5 filter, to avoid undercounting c).
        ac_rows = session.execute(text("""
            SELECT vs.symptom, COUNT(DISTINCT vr.vaers_id) AS ac
            FROM vaers_reports vr
            JOIN vaers_symptoms vs ON vr.vaers_id = vs.vaers_id
            WHERE vr.data_year = :year AND vs.symptom IS NOT NULL
            GROUP BY vs.symptom
        """), {"year": year}).fetchall()
        ac_map = {r[0]: float(r[1]) for r in ac_rows}
        df["ac"] = df["symptom"].map(ac_map).fillna(df["a"])
        df["c"] = (df["ac"] - df["a"]).clip(lower=0)

        # N: total DISTINCT reports in this year (used to derive d = N - b).
        N_row = session.execute(text(
            "SELECT COUNT(DISTINCT vaers_id) FROM vaers_reports WHERE data_year = :year"
        ), {"year": year}).fetchone()
        N = float(N_row[0]) if N_row and N_row[0] else df["b"].max()

        # d: total reports for all OTHER vax_types
        df["d"] = (N - df["b"]).clip(lower=1)

        # Drop rows where b or d is zero (can't compute PRR)
        df = df[(df["b"] > 0) & (df["d"] > 0) & (df["c"] >= 0)].copy()

        # PRR = (a/B) / (c/D)  where B = total drug reports, D = total other-drug reports
        df["prr"] = (df["a"] / df["b"]) / ((df["c"].clip(lower=1e-9)) / df["d"])

        # Yates-corrected chi-squared using the correct 2x2 contingency table:
        #
        #              Event     No Event    Total
        #   Drug:        a        B - a        B       (b in df = B)
        #   Not Drug:    c        D - c        D       (d in df = D)
        #   Total:      a+c    (B+D)-(a+c)    B+D
        #
        # chi2 = (|a*(D-c) - (B-a)*c| - N/2)^2 * N / (B * D * (a+c) * (B+D-a-c))
        _B = df["b"]
        _D = df["d"]
        _n12 = (_B - df["a"]).clip(lower=0)   # drug + no-event
        _n22 = (_D - df["c"]).clip(lower=0)   # other + no-event
        _N   = _B + _D                          # grand total (B + D)
        _n_dot1 = df["a"] + df["c"]            # column total: event
        _n_dot2 = _n12 + _n22                  # column total: no-event

        _num = ((df["a"] * _n22 - _n12 * df["c"]).abs() - _N / 2).clip(lower=0) ** 2 * _N
        _den = _B * _D * _n_dot1 * _n_dot2
        df["chi2"] = (_num / _den.clip(lower=1e-9)).round(4)
        df["prr"]  = df["prr"].round(4)

        now = datetime.utcnow()
        records = df[["vax_type", "symptom", "a", "serious_count", "prr", "chi2"]].to_dict("records")
        for i in tqdm(range(0, len(records), CHUNK_SIZE), desc=f"{year} ae_summary"):
            chunk = records[i:i + CHUNK_SIZE]
            session.execute(text("""
                INSERT INTO ae_summary
                  (data_year, vax_type, symptom, report_count, serious_count, prr, chi_squared, calculated_at)
                VALUES
                  (:year, :vax_type, :symptom, :a, :serious_count, :prr, :chi2, :calculated_at)
            """), [{"year": year, "calculated_at": now, **r} for r in chunk])
            session.commit()

        log.info("  Inserted %d ae_summary rows for %d", len(records), year)

    return len(years)


# ─── Entry point ──────────────────────────────────────────────────────────────

def main(years: list[int]):
    from shared.db import get_session

    log.info("═" * 60)
    log.info("VAERS Ingest started — %s", datetime.now().isoformat())
    log.info("Years to process: %s", years)
    log.info("Download dir: %s", DOWNLOAD_DIR)
    log.info("═" * 60)

    session = get_session()

    for year in years:
        log.info("─" * 40)
        log.info("Processing year %d …", year)
        zip_path = get_zip_path(year)
        if zip_path is None:
            log.warning("Skipping year %d — no file available", year)
            continue

        try:
            counts = load_year(session, year, zip_path)
            log.info(
                "Year %d loaded: %d reports, %d vaccines, %d symptoms",
                year, counts["reports"], counts["vaccines"], counts["symptoms"]
            )
        except Exception as exc:
            log.error("Error loading year %d: %s", year, exc, exc_info=True)
            session.rollback()

    compute_ae_summary(session, years)
    session.close()
    log.info("VAERS ingest complete")


if __name__ == "__main__":
    default_years_env = os.environ.get("VAERS_YEARS", str(datetime.now().year - 1))
    parser = argparse.ArgumentParser(description="Ingest VAERS adverse event data")
    parser.add_argument(
        "--years", type=str,
        default=default_years_env,
        help="Comma-separated list of years to process (e.g. 2021,2022,2023)"
    )
    parser.add_argument(
        "--data-dir", type=str, default=None,
        help=f"Directory for downloaded ZIP files (default: {DOWNLOAD_DIR})"
    )
    args = parser.parse_args()

    if args.data_dir:
        DOWNLOAD_DIR = Path(args.data_dir)
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    year_list = [int(y.strip()) for y in args.years.split(",")]
    main(year_list)
