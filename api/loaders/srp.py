"""Sustainable Rivers Program public metrics -> srp_footprint, srp_metrics, srp_sites (public-value proxy)."""

from pathlib import Path

import oracledb

from loaders.common import clip, read_json, record_load, replace_rows

FOOTPRINT_COLUMNS = [
    "snapshot_key", "as_of_year", "as_of_label", "rivers", "rivers_qualifier", "river_miles", "river_miles_qualifier",
    "reservoirs", "reservoirs_qualifier", "districts", "divisions", "floodplain_acres", "basis", "source", "source_url",
    "load_id",
]  # fmt: skip
METRIC_COLUMNS = [
    "metric_group", "metric_key", "label", "metric_value", "unit", "qualifier", "sort_order", "as_of_label",
    "as_of_year", "note", "source", "load_id",
]  # fmt: skip
SITE_COLUMNS = [
    "site_name", "river_name", "action_type", "org_code", "co_org_codes", "states", "infrastructure", "structures",
    "start_year", "implement_year", "incorporate_year", "orgs_engaged", "note", "source", "load_id",
]  # fmt: skip


def load(cur: oracledb.Cursor, data_dir: Path) -> dict[str, int]:
    doc = read_json(data_dir / "fixtures" / "srp" / "sustainable_rivers.json")
    meta = doc["_meta"]
    footprint, metrics, sites = doc["footprint"], doc["metrics"], doc["sites"]
    load_id = record_load(
        cur,
        meta,
        len(footprint) + len(metrics) + len(sites),
        f"{len(sites)} sites, {len(metrics)} program metrics, {len(footprint)} footprint snapshots transcribed from "
        f"{len(meta['documents'])} public HEC/ERDC documents",
    )
    cur.execute("SELECT code FROM organizations")
    known = {code for (code,) in cur}
    for s in sites:
        if s["org_code"] is not None and s["org_code"] not in known:
            raise ValueError(f"SRP site {s['site_name']!r} references unknown org {s['org_code']}")

    site_rows = [{**s, "note": clip(s["note"], 400), "load_id": load_id} for s in sites]
    replace_rows(cur, "srp_sites", SITE_COLUMNS, site_rows)
    replace_rows(cur, "srp_metrics", METRIC_COLUMNS, [{**m, "load_id": load_id} for m in metrics])
    replace_rows(cur, "srp_footprint", FOOTPRINT_COLUMNS, [{**f, "load_id": load_id} for f in footprint])
    return {"srp_sites": len(sites), "srp_metrics": len(metrics), "srp_footprint": len(footprint)}
