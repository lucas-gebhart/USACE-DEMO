"""Refresh the committed public-data fixtures under data/fixtures.

Every source here is public and stands in for an internal USACE system:

  USAspending (agency 096 + W912xx district contracts)  -> CEFMS proxy
  FY2025 O&M budget justification sheets (PDF)           -> P2 / work-plan proxy
  National Inventory of Dams (NID)                       -> BUILDER / asset proxy
  LPMS lock status + NTNI navigation notices (ORDS JSON) -> operations proxy

Usage:  python data/fetch.py [all|usaspending|jsheets|nid|lpms|ntni]

Only the standard library plus `pdftotext` (poppler-utils) is required, so this
script can run before the API project's virtualenv exists.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
FIX = HERE / "fixtures"
ORGS = HERE / "reference" / "orgs.csv"

UA = {"User-Agent": "USACE-DEMO fixture refresh (public data)"}

USASPENDING = "https://api.usaspending.gov/api/v2"
NID_CSV = "https://nid.sec.usace.army.mil/api/nation/csv"
LPMS = "https://ndc.ops.usace.army.mil/ords/lpms/lock_status_report_json?in_river_code={river}"
NTNI = "https://ndc.ops.usace.army.mil/ords/ntni/json_data/notices_by_district/{district}"
# Official URL (https://www.usace.army.mil/Portals/2/docs/civilworks/budget/FY2025-O&M.pdf)
# is behind Akamai and rejects scripted downloads; USACE's ContentDM mirror serves the same file.
JSHEETS_PDF = "https://usace.contentdm.oclc.org/utils/getfile/collection/p16021coll6/id/2486"

LPMS_RIVERS = ["MI", "OH", "IL", "TN", "CU", "MO", "AL", "AR", "GI"]
LPMS_MIN_INTERVAL_S = 13  # the ORDS endpoint enforces 5 requests / minute
NTNI_DISTRICTS = ["MVP", "MVR", "MVS", "MVM", "MVK", "MVN", "LRL", "LRH", "LRP", "LRN", "SAM", "SWL"]

NID_COLUMNS = [
    "Dam Name", "NID ID", "Owner Names", "Primary Owner Type", "Primary Purpose", "Purposes",
    "Latitude", "Longitude", "State", "County", "City", "River or Stream Name",
    "Congressional District", "Federal Agency Owners", "Federal Agency Involvement Regulatory",
    "Federal Agency Involvement Inspection", "Federal Agency Involvement Operation",
    "Primary Dam Type", "NID Height (Ft)", "Dam Length (Ft)", "Year Completed",
    "NID Storage (Acre-Ft)", "Max Storage (Acre-Ft)", "Drainage Area (Sq Miles)",
    "Number of Locks", "Last Inspection Date", "Inspection Frequency",
    "Hazard Potential Classification", "Condition Assessment", "Condition Assessment Date",
    "EAP Prepared", "EAP Last Revision Date", "Data Last Updated", "Website URL",
]
# Non-USACE dams are kept only for the Mississippi Valley Division states used in the drill-down beat.
NID_CONTEXT_STATES = {"Minnesota", "Wisconsin", "North Dakota", "Iowa", "Illinois", "Missouri",
                      "Tennessee", "Arkansas", "Mississippi", "Louisiana"}


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def get(url: str, *, data: dict | None = None, retries: int = 3) -> bytes:
    body = json.dumps(data).encode() if data is not None else None
    headers = dict(UA)
    if body is not None:
        headers["Content-Type"] = "application/json"
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=headers), timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            raise
    raise RuntimeError("unreachable")


def get_json(url: str, *, data: dict | None = None):
    # LPMS embeds raw newlines/tabs inside string values (lock notes), which strict JSON rejects.
    return json.loads(get(url, data=data), strict=False)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=False) + "\n")
    log(f"  wrote {path.relative_to(HERE.parent)} ({path.stat().st_size:,} bytes)")


def load_orgs() -> list[dict]:
    with ORGS.open(newline="") as f:
        return list(csv.DictReader(f))


def stamp(source: str, url: str, extra: dict | None = None) -> dict:
    meta = {"source": source, "url": url, "fetched_on": date.today().isoformat()}
    if extra:
        meta.update(extra)
    return meta


# --------------------------------------------------------------------------- USAspending

AWARD_FIELDS = [
    "Award ID", "Recipient Name", "Start Date", "End Date", "Award Amount", "Total Outlays",
    "Description", "Awarding Agency", "Awarding Sub Agency", "Contract Award Type",
    "Place of Performance State Code", "generated_internal_id", "NAICS", "PSC",
]


def fetch_usaspending(fy: int = 2025, awards_per_district: int = 40) -> None:
    out = FIX / "usaspending"
    for name, path in [
        ("agency_overview", f"/agency/096/?fiscal_year={fy}"),
        ("budgetary_resources", "/agency/096/budgetary_resources/"),
        ("federal_account", f"/agency/096/federal_account/?fiscal_year={fy}&limit=50"),
        ("program_activity", f"/agency/096/program_activity/?fiscal_year={fy}&limit=50"),
        ("object_class", f"/agency/096/object_class/?fiscal_year={fy}&limit=50"),
    ]:
        url = USASPENDING + path
        write_json(out / f"{name}.json", {"_meta": stamp("USAspending", url), **get_json(url)})

    awards: list[dict] = []
    office_check: dict[str, str | None] = {}
    for org in load_orgs():
        prefix = org["dodaac_prefix"]
        if not prefix:
            continue
        body = {
            "filters": {
                "award_type_codes": ["A", "B", "C", "D"],
                "agencies": [{"type": "awarding", "tier": "subtier", "name": "Department of the Army"}],
                "keywords": [prefix],
                "time_period": [{"start_date": f"{fy - 3}-10-01", "end_date": f"{fy + 1}-09-30"}],
            },
            "fields": AWARD_FIELDS,
            "limit": awards_per_district,
            "page": 1,
            "sort": "Award Amount",
            "order": "desc",
        }
        res = get_json(USASPENDING + "/search/spending_by_award/", data=body)
        rows = [r for r in res.get("results", []) if str(r.get("Award ID", "")).upper().startswith(prefix)]
        for r in rows:
            r["org_code"] = org["code"]
        awards.extend(rows)
        # One award detail per district confirms the DoDAAC -> district mapping via the awarding office name.
        if rows:
            detail = get_json(f"{USASPENDING}/awards/{rows[0]['generated_internal_id']}/")
            office_check[org["code"]] = (detail.get("awarding_agency") or {}).get("office_agency_name")
        log(f"  {org['code']} {prefix}: {len(rows)} contracts, office={office_check.get(org['code'])}")
    write_json(out / "district_contracts.json", {
        "_meta": stamp("USAspending spending_by_award", USASPENDING + "/search/spending_by_award/", {
            "filters": "awarding subtier 'Department of the Army', contract types A-D, keyword = district DoDAAC prefix",
            "fiscal_years": f"FY{fy - 2}-FY{fy + 1} period of performance overlap",
            "awarding_office_by_org": office_check,
        }),
        "results": awards,
    })


# --------------------------------------------------------------------------- FY2025 O&M J-sheets

MONEY = r"\$([\d,]+)"
RE_PROJECT = re.compile(r"^PROJECT NAME:\s*(.+?)\s*$", re.M)
RE_FY23 = re.compile(r"FISCAL YEAR 2023 ALLOCATION:\s*" + MONEY)
RE_FY24 = re.compile(r"ASSUMED FY 2024 ALLOCATION:\s*" + MONEY)
RE_IIJA = re.compile(r"\(IIJA\) FOR FY 2024:\s*" + MONEY)
RE_FY25 = re.compile(r"BUDGETED AMOUNT FOR FY 2025:\s*M:\s*" + MONEY + r"\s*O:\s*" + MONEY + r"\s*T:\s*" + MONEY)
RE_BL = re.compile(r"^\s*(ENS|FRM|HYD|NAV|REC|WTR):\s*" + MONEY, re.M)
RE_FOOTER = re.compile(r"^Division:\s*(.+?)\s{2,}District:\s*(.+?)\s{2,}", re.M)
RE_DESC = re.compile(r"LOCATION AND DESCRIPTION:\s*(.+?)(?:\n\s*\n|FISCAL YEAR 2023)", re.S)
RE_AUTH = re.compile(r"AUTHORIZATION:\s*(.+?)(?:\n\s*\n|LOCATION AND DESCRIPTION)", re.S)


def money(m: re.Match | None, group: int = 1) -> int | None:
    return int(m.group(group).replace(",", "")) if m else None


def fetch_jsheets() -> None:
    RAW.mkdir(exist_ok=True)
    pdf = RAW / "fy2025_om_jsheets.pdf"
    if not pdf.exists():
        log("  downloading FY2025 O&M justification sheets PDF")
        pdf.write_bytes(get(JSHEETS_PDF))
    if shutil.which("pdftotext") is None:
        sys.exit("pdftotext (poppler-utils) is required to parse the J-sheets PDF")
    text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], check=True, capture_output=True, text=True).stdout
    pages = text.split("\f")

    projects: list[dict] = []
    current: dict | None = None
    for page_no, page in enumerate(pages, start=1):
        m = RE_PROJECT.search(page)
        if m:
            name = re.sub(r"\s+\d/$", "", m.group(1))  # drop footnote markers such as "3/"
            state = name.rsplit(",", 1)[1].strip() if "," in name else ""
            desc = RE_DESC.search(page)
            auth = RE_AUTH.search(page)
            current = {
                "pdf_page": page_no,
                "project_name": name,
                "state": state,
                "division": None,
                "district": None,
                "authorization": " ".join(auth.group(1).split()) if auth else "",
                "description": " ".join(desc.group(1).split()) if desc else "",
                "fy2023_allocation": None,
                "fy2024_assumed_allocation": None,
                "fy2024_iija": None,
                "fy2025_maintenance": None,
                "fy2025_operations": None,
                "fy2025_total": None,
                "business_lines": {},
            }
            projects.append(current)
        if current is None:
            continue
        # Long justifications spill onto a second page, so the funding lines are searched on every page of the project.
        for key, rx in (("fy2023_allocation", RE_FY23), ("fy2024_assumed_allocation", RE_FY24), ("fy2024_iija", RE_IIJA)):
            if current[key] is None:
                current[key] = money(rx.search(page))
        if current["fy2025_total"] is None and (fy25 := RE_FY25.search(page)):
            current["fy2025_maintenance"], current["fy2025_operations"], current["fy2025_total"] = (
                money(fy25, 1), money(fy25, 2), money(fy25, 3))
        for bl, amt in RE_BL.findall(page):
            current["business_lines"][bl] = current["business_lines"].get(bl, 0) + int(amt.replace(",", ""))
        f = RE_FOOTER.search(page)
        if f and current["division"] is None:
            current["division"], current["district"] = f.group(1).strip(), f.group(2).strip()

    out = FIX / "workplan" / "fy2025_om_jsheets.json"
    write_json(out, {
        "_meta": stamp("FY2025 O&M budget justification sheets (Civil Works)", JSHEETS_PDF, {
            "official_url": "https://www.usace.army.mil/Portals/2/docs/civilworks/budget/FY2025-O&M.pdf",
            "document_date": "11 March 2024",
            "note": "President's Budget justification, not enacted work plan; amounts are whole dollars.",
            "projects_parsed": len(projects),
        }),
        "projects": projects,
    })
    missing = [p["project_name"] for p in projects if p["fy2025_total"] is None or p["district"] is None]
    log(f"  parsed {len(projects)} projects; {len(missing)} missing FY25 total or district: {missing[:5]}")


# --------------------------------------------------------------------------- NID

def fetch_nid() -> None:
    RAW.mkdir(exist_ok=True)
    raw = RAW / "nid.csv"
    if not raw.exists():
        log("  downloading NID national CSV (~70 MB)")
        raw.write_bytes(get(NID_CSV))
    out = FIX / "nid" / "dams.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with raw.open(newline="", encoding="utf-8-sig") as f:
        first = f.readline().strip()  # "Data Last Updated:,YYYY-M-D"
        reader = csv.DictReader(f)
        kept = 0
        with out.open("w", newline="") as o:
            w = csv.DictWriter(o, fieldnames=NID_COLUMNS, extrasaction="ignore")
            w.writeheader()
            for row in reader:
                usace_owned = row["Owner Names"].startswith("USACE - ")
                context = row["State"] in NID_CONTEXT_STATES and row["Hazard Potential Classification"] == "High"
                if usace_owned or context:
                    w.writerow(row)
                    kept += 1
    write_json(FIX / "nid" / "_meta.json", stamp("National Inventory of Dams", NID_CSV, {
        "data_last_updated": first.split(",", 1)[-1],
        "selection": "all dams whose Owner Names begins 'USACE - <District> District', plus High-hazard dams in "
                     "Mississippi Valley Division states as regional context",
        "rows": kept,
    }))
    log(f"  kept {kept} dams -> {out.relative_to(HERE.parent)}")


# --------------------------------------------------------------------------- LPMS / NTNI

def fetch_lpms() -> None:
    last = 0.0
    for river in LPMS_RIVERS:
        wait = LPMS_MIN_INTERVAL_S - (time.monotonic() - last)
        if wait > 0:
            time.sleep(wait)
        last = time.monotonic()
        url = LPMS.format(river=river)
        res = get_json(url)
        if isinstance(res, dict) and "error" in res:
            log(f"  {river}: {res['error']}")
            continue
        locks = sum(len(r.get("locks", [])) for r in res)
        if locks == 0:
            log(f"  {river}: no locks, skipped")
            continue
        write_json(FIX / "lpms" / f"lock_status_{river}.json", {"_meta": stamp("LPMS lock status (ORDS)", url), "rivers": res})


def fetch_ntni() -> None:
    for d in NTNI_DISTRICTS:
        url = NTNI.format(district=d)
        res = get_json(url)
        write_json(FIX / "ntni" / f"notices_{d}.json", {"_meta": stamp("NTNI navigation notices (ORDS)", url), **res})
        time.sleep(2)


STEPS = {"usaspending": fetch_usaspending, "jsheets": fetch_jsheets, "nid": fetch_nid, "lpms": fetch_lpms, "ntni": fetch_ntni}

if __name__ == "__main__":
    which = sys.argv[1:] or ["all"]
    for name in (STEPS if which == ["all"] else which):
        log(f"== {name}")
        STEPS[name]()
