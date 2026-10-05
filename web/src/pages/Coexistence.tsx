import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { api, type LegacyProject, type OrgRollup, type ProjectSummary } from "../lib/api";
import { useAuth } from "../lib/auth";
import { money } from "../lib/format";
import { ErrorBox, Loading, Section, StatusTag } from "../components/ui";

const APEX_SNIPPET = `-- APEX page 20 "District Dashboard", After-Submit process (PL/SQL)
DECLARE
  l_org organizations.code%TYPE := UPPER(:P20_ORG_CODE);
BEGIN
  IF NOT emt_security.user_can_see_org(:APP_USER, l_org) THEN
    apex_error.add_error(p_message => 'Not authorized', ...);
    RETURN;
  END IF;
  SELECT COUNT(*), TO_CHAR(SUM(fy2025_total), 'FML999G999G999G990')
    INTO :P20_PROJECT_COUNT, :P20_FY25_BUDGET
    FROM projects WHERE org_code = l_org;
  -- status label lives in emt_legacy.project_status_label
END;`;

const FASTAPI_SNIPPET = `# api/app/routers/orgs.py
@router.get("/{org_code}", response_model=DistrictDashboard)
def district_dashboard(org_code: str, user: User = Depends(current_user)):
    require_org_access(user, org_code)          # JWT claim, not session state
    pred, binds = services.org_scope(user, org_code)
    projects = services.with_status(db.query(  # Python port of the PL/SQL rule
        f"SELECT ... FROM projects WHERE {pred}", **binds))
    return DistrictDashboard(...)               # typed, OpenAPI-published

# tests/test_api.py asserts legacy and new routes agree row-for-row`;

export default function Coexistence() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const tree = useQuery({ queryKey: ["orgs", user?.username], queryFn: api.orgs });
  const districts: string[] = [];
  const walk = (o: OrgRollup) => {
    if (o.kind === "DISTRICT") districts.push(o.code);
    o.children.forEach(walk);
  };
  if (tree.data) walk(tree.data);
  const org = (params.get("org") ?? (user?.role === "DISTRICT" ? user.org_code : districts[0]) ?? "").toUpperCase();
  const legacy = useQuery({ queryKey: ["legacy", org], queryFn: () => api.legacyDashboard(org), enabled: !!org });
  const modern = useQuery({ queryKey: ["org", org], queryFn: () => api.org(org), enabled: !!org });

  return (
    <>
      <h1 className="font-heading-xl margin-bottom-0">APEX coexistence</h1>
      <p className="text-base-dark margin-top-05">
        Strangler-fig: the APEX-era package <code>emt_legacy</code> still runs in Oracle. FastAPI calls it through a{" "}
        <code>SYS_REFCURSOR</code> (left) while the rewritten route (right) reads the same tables. When the two agree the
        APEX page can be retired — and the test suite proves it on every commit.
      </p>

      <div className="grid-row grid-gap-2 margin-bottom-3">
        <div className="desktop:grid-col-6">
          <h2 className="font-heading-sm margin-bottom-05">Before — APEX page process (db/legacy/apex_page_process_example.sql)</h2>
          <pre className="emt-code">{APEX_SNIPPET}</pre>
        </div>
        <div className="desktop:grid-col-6">
          <h2 className="font-heading-sm margin-bottom-05">After — FastAPI route + test</h2>
          <pre className="emt-code">{FASTAPI_SNIPPET}</pre>
        </div>
      </div>

      <Section
        title="Live comparison"
        aside={
          <label className="usa-label display-inline margin-0">
            District{" "}
            <select
              className="usa-select display-inline-block width-card-lg margin-0"
              value={org}
              onChange={(e) => setParams({ org: e.target.value })}
            >
              {districts.length === 0 && <option value={org}>{org}</option>}
              {districts.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </label>
        }
      >
        {(legacy.isPending || modern.isPending) && <Loading what="both implementations" />}
        {legacy.error && <ErrorBox error={legacy.error} />}
        {modern.error && <ErrorBox error={modern.error} />}
        {legacy.data && modern.data && <Compare legacy={legacy.data.projects} modern={modern.data.projects} impl={legacy.data.implementation} />}
      </Section>
    </>
  );
}

function Compare({ legacy, modern, impl }: { legacy: LegacyProject[]; modern: ProjectSummary[]; impl: string }) {
  const byId = new Map(modern.map((p) => [p.project_id, p]));
  const rows = legacy.map((l) => ({ l, m: byId.get(l.project_id) }));
  const mismatches = rows.filter((r) => !r.m || r.m.status_label !== r.l.status_label || r.m.fy2025_total !== r.l.fy2025_total);
  return (
    <>
      <div className={`usa-alert usa-alert--slim ${mismatches.length ? "usa-alert--warning" : "usa-alert--success"} margin-bottom-2`}>
        <div className="usa-alert__body">
          <p className="usa-alert__text">
            {mismatches.length === 0
              ? `${rows.length} projects: PL/SQL and FastAPI agree on every FY25 total and status label.`
              : `${mismatches.length} of ${rows.length} rows differ between implementations.`}
          </p>
        </div>
      </div>
      <div className="usa-table-container--scrollable" tabIndex={0}>
        <table className="usa-table usa-table--compact usa-table--striped width-full font-body-2xs">
          <thead>
            <tr>
              <th scope="col">Project</th>
              <th scope="col" colSpan={2} className="text-center bg-base-lightest">
                {impl}
              </th>
              <th scope="col" colSpan={2} className="text-center bg-primary-lighter">
                FastAPI · services.project_status_label
              </th>
              <th scope="col">Match</th>
            </tr>
            <tr>
              <th scope="col"></th>
              <th scope="col" className="text-right bg-base-lightest">FY25 total</th>
              <th scope="col" className="bg-base-lightest">Status</th>
              <th scope="col" className="text-right bg-primary-lighter">FY25 total</th>
              <th scope="col" className="bg-primary-lighter">Status</th>
              <th scope="col"></th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ l, m }) => {
              const ok = m && m.status_label === l.status_label && m.fy2025_total === l.fy2025_total;
              return (
                <tr key={l.project_id}>
                  <td>{l.name}</td>
                  <td className="text-right">{money(l.fy2025_total)}</td>
                  <td>
                    <StatusTag label={l.status_label} />
                  </td>
                  <td className="text-right">{money(m?.fy2025_total)}</td>
                  <td>{m ? <StatusTag label={m.status_label} /> : "—"}</td>
                  <td>{ok ? <span className="text-green">✓</span> : <span className="text-secondary">differs</span>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
