// Typed client for the FastAPI tier. Types mirror api/app/models.py (also published at /api/openapi.json).

export interface SourceLoad {
  load_id: number;
  source: string;
  source_url: string;
  fetched_on: string;
  loaded_at: string;
  row_count: number;
  note: string | null;
}

export interface Org {
  code: string;
  name: string;
  kind: "HQ" | "DIVISION" | "DISTRICT";
  parent_code: string | null;
  dodaac_prefix: string | null;
  states: string | null;
}

export interface OrgRollup extends Org {
  project_count: number;
  fy2025_budget: number;
  contract_count: number;
  contract_value: number;
  contract_outlays: number;
  asset_count: number;
  notice_count: number;
  children: OrgRollup[];
}

export interface BusinessLine {
  business_line: string;
  amount: number;
}

export type StatusLabel = "GROWING" | "SHRINKING" | "STEADY" | "UNKNOWN";

export interface ProjectSummary {
  project_id: number;
  name: string;
  state: string | null;
  org_code: string | null;
  district_name: string | null;
  division_name: string | null;
  fy2023_allocation: number | null;
  fy2024_assumed: number | null;
  fy2024_iija: number | null;
  fy2025_maintenance: number | null;
  fy2025_operations: number | null;
  fy2025_total: number | null;
  status_label: StatusLabel;
}

export interface Project extends ProjectSummary {
  authorization: string | null;
  description: string | null;
  source_page: number | null;
  business_lines: BusinessLine[];
  source: SourceLoad | null;
}

export interface Contract {
  piid: string;
  org_code: string | null;
  recipient_name: string | null;
  description: string | null;
  start_date: string | null;
  end_date: string | null;
  award_amount: number | null;
  total_outlays: number | null;
  award_type: string | null;
  pop_state: string | null;
  naics_code: string | null;
  naics_desc: string | null;
  psc_code: string | null;
  psc_desc: string | null;
  usaspending_id: string | null;
  usaspending_url: string | null;
}

export interface Asset {
  nid_id: string;
  name: string;
  org_code: string | null;
  owner_names: string | null;
  primary_purpose: string | null;
  state: string | null;
  county: string | null;
  river: string | null;
  dam_type: string | null;
  nid_height_ft: number | null;
  year_completed: number | null;
  nid_storage_af: number | null;
  last_inspection: string | null;
  hazard: string | null;
  condition: string | null;
  condition_date: string | null;
  eap_status: string | null;
  latitude: number | null;
  longitude: number | null;
}

export interface LockObservation {
  observation_id: number;
  river_code: string;
  river_name: string | null;
  lock_number: string;
  lock_name: string | null;
  lock_mile: number | null;
  reading_at: string | null;
  upper_gage_ft: number | null;
  lower_gage_ft: number | null;
  pending_arrivals: number | null;
  locking_now: number | null;
  locked_up_24h: number | null;
  locked_down_24h: number | null;
  avg_delay_24h_min: number | null;
  notes: string | null;
}

export interface River {
  river_code: string;
  river_name: string | null;
  locks: number;
  pending_arrivals: number | null;
  avg_delay_24h_min: number | null;
}

export interface NavNotice {
  notice_no: string;
  org_code: string | null;
  control_number: number | null;
  issue_date: string | null;
  begin_date: string | null;
  waterways: string | null;
  notice_url: string | null;
}

export interface NamedAmount {
  name: string;
  obligated: number | null;
  gross_outlays: number | null;
}

export interface FederalAccount extends NamedAmount {
  account_code: string;
}

export interface BudgetYear {
  fiscal_year: number;
  budgetary_resources: number | null;
  obligations: number | null;
  outlays: number | null;
  obligations_by_period: { period: number; obligated: number | null }[];
}

export interface MixEntry {
  label: string;
  count: number;
}

export interface LockSummary {
  locks_reporting?: number;
  pending_arrivals?: number | null;
  lockages_24h?: number | null;
  avg_delay_24h_min?: number | null;
  latest_reading?: string | null;
}

export interface Portfolio {
  scope: Org;
  budget_years: BudgetYear[];
  federal_accounts: FederalAccount[];
  program_activities: NamedAmount[];
  object_classes: NamedAmount[];
  rollup: OrgRollup;
  business_line_mix: BusinessLine[];
  hazard_mix: MixEntry[];
  condition_mix: MixEntry[];
  lock_summary: LockSummary;
  sources: SourceLoad[];
}

export interface DistrictDashboard {
  org: Org;
  rollup: OrgRollup;
  hazard_mix: MixEntry[];
  condition_mix: MixEntry[];
  projects: ProjectSummary[];
  contracts: Contract[];
  notices: NavNotice[];
  sources: SourceLoad[];
}

export interface LegacyProject {
  project_id: number;
  name: string;
  state: string | null;
  fy2024_assumed: number | null;
  fy2025_total: number | null;
  status_label: StatusLabel;
  business_lines: BusinessLine[];
}

export interface LegacyDashboard {
  org_code: string;
  implementation: string;
  projects: LegacyProject[];
}

export interface Workforce {
  fiscal_year: number;
  personnel_object_classes: NamedAmount[];
  personnel_obligated: number;
  total_obligated: number;
  personnel_share: number | null;
  caveat: string;
}

export interface DevUser {
  username: string;
  display_name: string;
  role: "HQ" | "DIVISION" | "DISTRICT";
  org_code: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: DevUser;
}

export interface RelatedRecords {
  match_basis: string;
  contracts: Contract[];
  assets: Asset[];
}

const BASE = "/api";
const TOKEN_KEY = "emt.token";

export const token = {
  get: () => sessionStorage.getItem(TOKEN_KEY),
  set: (t: string) => sessionStorage.setItem(TOKEN_KEY, t),
  clear: () => sessionStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body) headers.set("Content-Type", "application/json");
  const t = token.get();
  if (t) headers.set("Authorization", `Bearer ${t}`);
  const res = await fetch(BASE + path, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = ((await res.json()) as { detail?: string }).detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    if (res.status === 401) token.clear();
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

const qs = (params: Record<string, string | number | boolean | undefined | null>) => {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") s.set(k, String(v));
  const out = s.toString();
  return out ? `?${out}` : "";
};

export const api = {
  devUsers: () => request<DevUser[]>("/auth/users"),
  login: (username: string, password: string) =>
    request<TokenResponse>("/auth/token", { method: "POST", body: JSON.stringify({ username, password }) }),
  me: () => request<DevUser>("/auth/me"),
  portfolio: () => request<Portfolio>("/v1/portfolio"),
  orgs: () => request<OrgRollup>("/v1/orgs"),
  org: (code: string) => request<DistrictDashboard>(`/v1/orgs/${code}`),
  projects: (p: { org?: string; q?: string; status?: string; limit?: number }) =>
    request<ProjectSummary[]>(`/v1/projects${qs(p)}`),
  project: (id: number) => request<Project>(`/v1/projects/${id}`),
  related: (id: number) => request<RelatedRecords>(`/v1/projects/${id}/related`),
  contracts: (p: { org?: string; q?: string; active_on?: string; limit?: number }) =>
    request<Contract[]>(`/v1/contracts${qs(p)}`),
  assets: (p: { org?: string; state?: string; hazard?: string; condition?: string; usace_only?: boolean; limit?: number }) =>
    request<Asset[]>(`/v1/assets${qs(p)}`),
  locks: (river?: string) => request<LockObservation[]>(`/v1/ops/locks${qs({ river })}`),
  rivers: () => request<River[]>("/v1/ops/rivers"),
  notices: (p: { org?: string; limit?: number }) => request<NavNotice[]>(`/v1/ops/notices${qs(p)}`),
  workforce: () => request<Workforce>("/v1/workforce"),
  legacyDashboard: (code: string) => request<LegacyDashboard>(`/v1/legacy/district-dashboard/${code}`),
  sources: () => request<SourceLoad[]>("/v1/sources"),
};
