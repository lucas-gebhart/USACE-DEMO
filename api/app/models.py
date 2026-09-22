"""Response schemas. These are the API contract the React client builds against and what OpenAPI publishes."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class SourceLoad(BaseModel):
    load_id: int
    source: str
    source_url: str
    fetched_on: date
    loaded_at: datetime
    row_count: int
    note: str | None = None


class Org(BaseModel):
    code: str
    name: str
    kind: str
    parent_code: str | None = None
    dodaac_prefix: str | None = None
    states: str | None = None


class OrgRollup(Org):
    project_count: int
    fy2025_budget: float
    contract_count: int
    contract_value: float
    contract_outlays: float
    asset_count: int
    notice_count: int
    children: list[OrgRollup] = []


class BusinessLine(BaseModel):
    business_line: str
    amount: float


class ProjectSummary(BaseModel):
    project_id: int
    name: str
    state: str | None = None
    org_code: str | None = None
    district_name: str | None = None
    division_name: str | None = None
    fy2023_allocation: float | None = None
    fy2024_assumed: float | None = None
    fy2024_iija: float | None = None
    fy2025_maintenance: float | None = None
    fy2025_operations: float | None = None
    fy2025_total: float | None = None
    status_label: str


class Project(ProjectSummary):
    authorization: str | None = None
    description: str | None = None
    source_page: int | None = None
    business_lines: list[BusinessLine]
    source: SourceLoad | None = None


class Contract(BaseModel):
    piid: str
    org_code: str | None = None
    recipient_name: str | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    award_amount: float | None = None
    total_outlays: float | None = None
    award_type: str | None = None
    pop_state: str | None = None
    naics_code: str | None = None
    naics_desc: str | None = None
    psc_code: str | None = None
    psc_desc: str | None = None
    usaspending_id: str | None = None
    usaspending_url: str | None = None


class Asset(BaseModel):
    nid_id: str
    name: str
    org_code: str | None = None
    owner_names: str | None = None
    primary_purpose: str | None = None
    state: str | None = None
    county: str | None = None
    river: str | None = None
    dam_type: str | None = None
    nid_height_ft: float | None = None
    year_completed: int | None = None
    nid_storage_af: float | None = None
    last_inspection: date | None = None
    hazard: str | None = None
    condition: str | None = None
    condition_date: date | None = None
    eap_status: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class LockObservation(BaseModel):
    observation_id: int
    river_code: str
    river_name: str | None = None
    lock_number: str
    lock_name: str | None = None
    lock_mile: float | None = None
    reading_at: datetime | None = None
    upper_gage_ft: float | None = None
    lower_gage_ft: float | None = None
    pending_arrivals: int | None = None
    locking_now: int | None = None
    locked_up_24h: int | None = None
    locked_down_24h: int | None = None
    avg_delay_24h_min: float | None = None
    notes: str | None = None


class NavNotice(BaseModel):
    notice_no: str
    org_code: str | None = None
    control_number: int | None = None
    issue_date: datetime | None = None
    begin_date: datetime | None = None
    waterways: str | None = None
    notice_url: str | None = None


class NamedAmount(BaseModel):
    name: str
    obligated: float | None = None
    gross_outlays: float | None = None


class FederalAccount(NamedAmount):
    account_code: str


class BudgetYear(BaseModel):
    fiscal_year: int
    budgetary_resources: float | None = None
    obligations: float | None = None
    outlays: float | None = None
    obligations_by_period: list[dict] = []


class MixEntry(BaseModel):
    label: str
    count: int


class Portfolio(BaseModel):
    scope: Org
    budget_years: list[BudgetYear]
    federal_accounts: list[FederalAccount]
    program_activities: list[NamedAmount]
    object_classes: list[NamedAmount]
    rollup: OrgRollup
    business_line_mix: list[BusinessLine]
    hazard_mix: list[MixEntry]
    condition_mix: list[MixEntry]
    lock_summary: dict
    sources: list[SourceLoad]


class DistrictDashboard(BaseModel):
    org: Org
    rollup: OrgRollup
    hazard_mix: list[MixEntry]
    condition_mix: list[MixEntry]
    projects: list[ProjectSummary]
    contracts: list[Contract]
    notices: list[NavNotice]
    sources: list[SourceLoad]
