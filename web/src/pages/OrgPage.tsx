import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { day, int, money, moneyCompact, when } from "../lib/format";
import { ErrorBox, Loading, OrgLink, ProxyBanner, Section, SourceTable, Stat, StatusTag } from "../components/ui";

export default function OrgPage() {
  const { code = "" } = useParams();
  const q = useQuery({ queryKey: ["org", code], queryFn: () => api.org(code) });
  if (q.isPending) return <Loading what={code} />;
  if (q.error) return <ErrorBox error={q.error} />;
  const d = q.data;

  return (
    <>
      <nav className="usa-breadcrumb usa-breadcrumb--wrap padding-0" aria-label="Breadcrumbs">
        <ol className="usa-breadcrumb__list">
          <li className="usa-breadcrumb__list-item">
            <Link className="usa-breadcrumb__link" to="/">
              Enterprise
            </Link>
          </li>
          {d.org.parent_code && d.org.parent_code !== "HQ" && (
            <li className="usa-breadcrumb__list-item">
              <Link className="usa-breadcrumb__link" to={`/orgs/${d.org.parent_code}`}>
                {d.org.parent_code}
              </Link>
            </li>
          )}
          <li className="usa-breadcrumb__list-item usa-current" aria-current="page">
            <span>{d.org.code}</span>
          </li>
        </ol>
      </nav>
      <h1 className="font-heading-xl margin-y-0">{d.org.name}</h1>
      <p className="text-base-dark margin-top-05">
        {d.org.kind} {d.org.dodaac_prefix && <>· DoDAAC {d.org.dodaac_prefix}</>} {d.org.states && <>· {d.org.states}</>}
        {" · "}
        <Link className="usa-link" to={`/coexistence?org=${d.org.code}`}>
          compare with the APEX PL/SQL result
        </Link>
      </p>

      <div className="grid-row grid-gap-2 margin-bottom-3">
        <div className="tablet:grid-col">
          <Stat label="FY25 O&M projects" value={int(d.rollup.project_count)} />
        </div>
        <div className="tablet:grid-col">
          <Stat label="FY25 O&M budget" value={moneyCompact(d.rollup.fy2025_budget)} />
        </div>
        <div className="tablet:grid-col">
          <Stat label="Awards" value={int(d.rollup.contract_count)} hint={moneyCompact(d.rollup.contract_value)} />
        </div>
        <div className="tablet:grid-col">
          <Stat label="USACE dams" value={int(d.rollup.asset_count)} />
        </div>
        <div className="tablet:grid-col">
          <Stat label="Nav notices" value={int(d.rollup.notice_count)} />
        </div>
      </div>

      {d.rollup.children.length > 0 && (
        <Section title="Subordinate organizations">
          <ul className="usa-list usa-list--unstyled display-flex flex-wrap">
            {d.rollup.children.map((c) => (
              <li key={c.code} className="margin-right-2 margin-bottom-1">
                <OrgLink code={c.code} name={`${c.code} · ${c.name}`} />{" "}
                <span className="text-base font-body-2xs">
                  {int(c.project_count)} proj · {moneyCompact(c.fy2025_budget)}
                </span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      <Section title="FY2025 O&M projects" aside="P2 / CMP proxy — FY25 justification sheets">
        <div className="usa-table-container--scrollable" tabIndex={0}>
          <table className="usa-table usa-table--compact usa-table--striped width-full font-body-2xs">
            <thead>
              <tr>
                <th scope="col">Project</th>
                <th scope="col">State</th>
                {d.org.kind !== "DISTRICT" && <th scope="col">District</th>}
                <th scope="col" className="text-right">FY23 alloc</th>
                <th scope="col" className="text-right">FY24 assumed</th>
                <th scope="col" className="text-right">FY25 total</th>
                <th scope="col">Status</th>
              </tr>
            </thead>
            <tbody>
              {d.projects.map((p) => (
                <tr key={p.project_id}>
                  <td>
                    <Link className="usa-link" to={`/projects/${p.project_id}`}>
                      {p.name}
                    </Link>
                  </td>
                  <td>{p.state}</td>
                  {d.org.kind !== "DISTRICT" && <td>{p.org_code && <OrgLink code={p.org_code} />}</td>}
                  <td className="text-right">{money(p.fy2023_allocation)}</td>
                  <td className="text-right">{money(p.fy2024_assumed)}</td>
                  <td className="text-right">{money(p.fy2025_total)}</td>
                  <td>
                    <StatusTag label={p.status_label} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Largest contract awards" aside="CEFMS proxy — USAspending, Army awards by district DoDAAC">
        <ProxyBanner>
          Awards come from USAspending filtered on this district's DoDAAC prefix. They are public contract actions, not
          CEFMS obligations or disbursements.
        </ProxyBanner>
        <div className="usa-table-container--scrollable" tabIndex={0}>
          <table className="usa-table usa-table--compact usa-table--striped width-full font-body-2xs">
            <thead>
              <tr>
                <th scope="col">PIID</th>
                <th scope="col">Recipient</th>
                <th scope="col">Description</th>
                <th scope="col">Period</th>
                <th scope="col" className="text-right">Award</th>
                <th scope="col" className="text-right">Outlays</th>
              </tr>
            </thead>
            <tbody>
              {d.contracts.slice(0, 15).map((c) => (
                <tr key={c.piid}>
                  <td>
                    {c.usaspending_url ? (
                      <a className="usa-link" href={c.usaspending_url} target="_blank" rel="noreferrer">
                        {c.piid}
                      </a>
                    ) : (
                      c.piid
                    )}
                  </td>
                  <td>{c.recipient_name}</td>
                  <td className="emt-clamp">{c.description}</td>
                  <td className="text-no-wrap">
                    {day(c.start_date)} → {day(c.end_date)}
                  </td>
                  <td className="text-right">{money(c.award_amount)}</td>
                  <td className="text-right">{money(c.total_outlays)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <div className="grid-row grid-gap-2">
        <div className="desktop:grid-col-6">
          <Section title="Navigation notices" aside="NTNI (live USACE ORDS/APEX feed)">
            {d.notices.length === 0 ? (
              <p className="text-base">No NTNI notices for this scope.</p>
            ) : (
              <ul className="usa-list usa-list--unstyled font-body-2xs">
                {d.notices.slice(0, 10).map((n) => (
                  <li key={n.notice_no} className="border-bottom border-base-lighter padding-y-05">
                    <a className="usa-link" href={n.notice_url ?? "#"} target="_blank" rel="noreferrer">
                      {n.notice_no}
                    </a>{" "}
                    — {n.waterways} <span className="text-base">· {when(n.issue_date)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Section>
        </div>
        <div className="desktop:grid-col-6">
          <Section title="Dam hazard mix" aside="NID, USACE-owned">
            <table className="usa-table usa-table--compact width-full font-body-2xs">
              <tbody>
                {d.hazard_mix.map((h) => (
                  <tr key={h.label}>
                    <td>{h.label}</td>
                    <td className="text-right">{int(h.count)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>
        </div>
      </div>

      <Section title="Lineage">
        <SourceTable sources={d.sources} />
      </Section>
    </>
  );
}
