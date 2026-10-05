"""Business logic that used to live in PL/SQL / APEX page processes, now versioned Python.

`project_status_label` is the direct port of emt_legacy.project_status_label; the
test-suite asserts both implementations agree row-for-row against Oracle. Money
math uses Decimal so thresholds behave like Oracle NUMBER (100 * 1.10 is exactly
110, which binary floats get wrong).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app import db
from app.auth import User, visible_orgs
from app.models import BusinessLine, MixEntry, OrgRollup, SourceLoad

USASPENDING_AWARD_URL = "https://www.usaspending.gov/award/{id}"


def project_status_label(fy2024: float | Decimal | None, fy2025: float | Decimal | None) -> str:
    if fy2025 is None or fy2024 is None or fy2024 == 0:
        return "UNKNOWN"
    prior, current = Decimal(str(fy2024)), Decimal(str(fy2025))
    if current >= prior * Decimal("1.10"):
        return "GROWING"
    if current <= prior * Decimal("0.90"):
        return "SHRINKING"
    return "STEADY"


def with_status(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for r in rows:
        r["status_label"] = project_status_label(r.get("fy2024_assumed"), r.get("fy2025_total"))
    return rows


def with_award_url(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for r in rows:
        r["usaspending_url"] = USASPENDING_AWARD_URL.format(id=r["usaspending_id"]) if r.get("usaspending_id") else None
    return rows


Scope = tuple[str, dict[str, Any]]


def org_scope(user: User, org_code: str | None = None, column: str = "org_code") -> Scope:
    """SQL predicate + binds limiting rows to `org_code`'s subtree (default: the user's own).

    HQ with no explicit org sees every row, including ones no district owns.
    Callers must have checked `require_org_access` before passing a foreign org_code.
    """
    root = org_code or user.org_code
    if root == "HQ":
        return "1 = 1", {}
    codes = sorted(visible_orgs(root))
    binds = {f"o{i}": c for i, c in enumerate(codes)}
    return f"{column} IN (" + ", ".join(f":{k}" for k in binds) + ")", binds


def rollup_tree(root: str) -> OrgRollup:
    """Org tree rooted at `root` with counts summed upward from districts."""
    rows = db.query("SELECT * FROM v_org_rollup")
    by_code = {r["code"]: r for r in rows}
    for r in rows:
        r["children"] = []
    for r in rows:
        parent = by_code.get(r["parent_code"] or "")
        if parent is not None:
            parent["children"].append(r)
    measures = (
        "project_count",
        "fy2025_budget",
        "contract_count",
        "contract_value",
        "contract_outlays",
        "asset_count",
        "notice_count",
    )

    def build(node: dict) -> OrgRollup:
        children = sorted((build(c) for c in node["children"]), key=lambda c: c.code)
        totals = {m: node[m] + sum(getattr(c, m) for c in children) for m in measures}
        return OrgRollup(**{**node, **totals, "children": children})

    return build(by_code[root])


def mix(scope: Scope, column: str) -> list[MixEntry]:
    pred, binds = scope
    rows = db.query(
        f"SELECT NVL({column}, 'Not Available') AS label, COUNT(*) AS count FROM assets"
        f" WHERE {pred} GROUP BY NVL({column}, 'Not Available') ORDER BY count DESC",
        **binds,
    )
    return [MixEntry(**r) for r in rows]


def business_line_mix(scope: Scope) -> list[BusinessLine]:
    pred, binds = scope
    rows = db.query(
        f"""SELECT b.business_line, SUM(b.amount) AS amount
              FROM project_business_lines b JOIN projects p ON p.project_id = b.project_id
             WHERE {pred}
             GROUP BY b.business_line ORDER BY amount DESC""",
        **binds,
    )
    return [BusinessLine(**r) for r in rows]


def sources() -> list[SourceLoad]:
    rows = db.query(
        """SELECT * FROM (
             SELECT s.*, ROW_NUMBER() OVER (PARTITION BY source, source_url ORDER BY loaded_at DESC) rn
               FROM source_loads s)
           WHERE rn = 1 ORDER BY source, source_url"""
    )
    return [SourceLoad(**{k: v for k, v in r.items() if k != "rn"}) for r in rows]
