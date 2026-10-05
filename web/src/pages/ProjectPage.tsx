import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { BUSINESS_LINES, day, int, money } from "../lib/format";
import { ErrorBox, Loading, OrgLink, ProxyBanner, Section, Stat, StatusTag } from "../components/ui";

export default function ProjectPage() {
  const { id = "0" } = useParams();
  const pid = Number(id);
  const q = useQuery({ queryKey: ["project", pid], queryFn: () => api.project(pid) });
  const rel = useQuery({ queryKey: ["related", pid], queryFn: () => api.related(pid) });
  if (q.isPending) return <Loading what="project" />;
  if (q.error) return <ErrorBox error={q.error} />;
  const p = q.data;

  return (
    <>
      <nav className="usa-breadcrumb usa-breadcrumb--wrap padding-0" aria-label="Breadcrumbs">
        <ol className="usa-breadcrumb__list">
          <li className="usa-breadcrumb__list-item">
            <Link className="usa-breadcrumb__link" to="/">
              Enterprise
            </Link>
          </li>
          {p.org_code && (
            <li className="usa-breadcrumb__list-item">
              <Link className="usa-breadcrumb__link" to={`/orgs/${p.org_code}`}>
                {p.org_code}
              </Link>
            </li>
          )}
          <li className="usa-breadcrumb__list-item usa-current" aria-current="page">
            <span>Project {p.project_id}</span>
          </li>
        </ol>
      </nav>
      <h1 className="font-heading-xl margin-y-0">{p.name}</h1>
      <p className="text-base-dark margin-top-05">
        {p.district_name} ({p.org_code && <OrgLink code={p.org_code} />}) · {p.division_name} · {p.state} ·{" "}
        <StatusTag label={p.status_label} />
      </p>

      <div className="grid-row grid-gap-2 margin-bottom-3">
        <div className="tablet:grid-col">
          <Stat label="FY23 allocation" value={money(p.fy2023_allocation)} />
        </div>
        <div className="tablet:grid-col">
          <Stat label="FY24 assumed" value={money(p.fy2024_assumed)} hint={p.fy2024_iija ? `+ IIJA ${money(p.fy2024_iija)}` : undefined} />
        </div>
        <div className="tablet:grid-col">
          <Stat label="FY25 maintenance" value={money(p.fy2025_maintenance)} />
        </div>
        <div className="tablet:grid-col">
          <Stat label="FY25 operations" value={money(p.fy2025_operations)} />
        </div>
        <div className="tablet:grid-col">
          <Stat label="FY25 total" value={money(p.fy2025_total)} />
        </div>
      </div>

      <div className="grid-row grid-gap-2">
        <div className="desktop:grid-col-8">
          <Section title="Justification sheet">
            {p.authorization && (
              <p className="font-body-2xs">
                <strong>Authorization:</strong> {p.authorization}
              </p>
            )}
            <p className="font-body-sm line-height-sans-4">{p.description}</p>
            {p.source && (
              <p className="font-body-2xs text-base">
                Source:{" "}
                <a className="usa-link" href={p.source.source_url} target="_blank" rel="noreferrer">
                  {p.source.source}
                </a>
                {p.source_page && <> · PDF page {p.source_page}</>} · fetched {day(p.source.fetched_on)}
              </p>
            )}
          </Section>
        </div>
        <div className="desktop:grid-col-4">
          <Section title="Business lines">
            <table className="usa-table usa-table--compact width-full font-body-2xs">
              <tbody>
                {p.business_lines.map((b) => (
                  <tr key={b.business_line}>
                    <td>
                      {BUSINESS_LINES[b.business_line] ?? b.business_line} <span className="text-base">({b.business_line})</span>
                    </td>
                    <td className="text-right">{money(b.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>
          <Section title="Status rule">
            <p className="font-body-2xs margin-0">
              <code>status_label</code> is FY25 total vs FY24 assumed: ≥110% GROWING, ≤90% SHRINKING, else STEADY. The same
              rule runs in PL/SQL (<code>emt_legacy.project_status_label</code>) and in Python (
              <code>services.project_status_label</code>); the test suite asserts they agree.
            </p>
          </Section>
        </div>
      </div>

      <Section title="Related records (heuristic linkage)">
        <ProxyBanner>
          Public sources carry no shared project key. Contracts and dams below are matched by district, state and a
          leading keyword{rel.data && <> — {rel.data.match_basis}</>}. In the enclave this would be a P2 ↔ CEFMS ↔ BUILDER
          join.
        </ProxyBanner>
        {rel.isPending && <Loading what="related records" />}
        {rel.error && <ErrorBox error={rel.error} />}
        {rel.data && (
          <div className="grid-row grid-gap-2">
            <div className="desktop:grid-col-7">
              <h3 className="font-heading-sm margin-bottom-05">Contract awards in {p.org_code}</h3>
              <table className="usa-table usa-table--compact usa-table--striped width-full font-body-2xs emt-table-fixed">
                <thead>
                  <tr>
                    <th scope="col" className="width-card">PIID</th>
                    <th scope="col" className="width-card-lg">Recipient</th>
                    <th scope="col">Description</th>
                    <th scope="col" className="text-right width-card">Award</th>
                  </tr>
                </thead>
                <tbody>
                  {rel.data.contracts.map((c) => (
                    <tr key={c.piid}>
                      <td>
                        <a className="usa-link" href={c.usaspending_url ?? "#"} target="_blank" rel="noreferrer">
                          {c.piid}
                        </a>
                      </td>
                      <td>{c.recipient_name}</td>
                      <td className="emt-clamp">{c.description}</td>
                      <td className="text-right">{money(c.award_amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="desktop:grid-col-5">
              <h3 className="font-heading-sm margin-bottom-05">USACE dams in {p.state}</h3>
              <table className="usa-table usa-table--compact usa-table--striped width-full font-body-2xs">
                <thead>
                  <tr>
                    <th scope="col">Dam</th>
                    <th scope="col">Hazard</th>
                    <th scope="col">Condition</th>
                    <th scope="col" className="text-right">Storage (af)</th>
                  </tr>
                </thead>
                <tbody>
                  {rel.data.assets.map((a) => (
                    <tr key={a.nid_id}>
                      <td>
                        {a.name} <span className="text-base">{a.nid_id}</span>
                      </td>
                      <td>{a.hazard}</td>
                      <td>{a.condition}</td>
                      <td className="text-right">{int(a.nid_storage_af)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Section>
    </>
  );
}
