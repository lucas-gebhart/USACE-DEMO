import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { dec1, int, when } from "../lib/format";
import { ErrorBox, Loading, OrgLink, ProxyBanner, Section, Stat } from "../components/ui";

export default function Operations() {
  const { user } = useAuth();
  const [river, setRiver] = useState("MI");
  const rivers = useQuery({ queryKey: ["rivers"], queryFn: api.rivers });
  const locks = useQuery({ queryKey: ["locks", river], queryFn: () => api.locks(river) });
  const notices = useQuery({ queryKey: ["notices", user?.username], queryFn: () => api.notices({ limit: 50 }) });
  const workforce = useQuery({ queryKey: ["workforce"], queryFn: api.workforce });

  return (
    <>
      <h1 className="font-heading-xl margin-bottom-0">Operations &amp; workforce</h1>
      <p className="text-base-dark margin-top-05">
        The "before" for this page is USACE's own public APEX/ORDS app (Corps Locks,{" "}
        <a className="usa-link" href="https://ndc.ops.usace.army.mil/ords/f?p=108" target="_blank" rel="noreferrer">
          ndc.ops.usace.army.mil/ords/f?p=108
        </a>
        ). Same feed, rendered from a typed FastAPI route instead of an APEX interactive report.
      </p>

      <Section
        title="Lock status (LPMS snapshot)"
        aside={
          <label className="usa-label display-inline margin-0">
            River{" "}
            <select className="usa-select display-inline-block width-card margin-0" value={river} onChange={(e) => setRiver(e.target.value)}>
              {rivers.data?.map((r) => (
                <option key={r.river_code} value={r.river_code}>
                  {r.river_code} · {r.river_name} ({r.locks})
                </option>
              ))}
            </select>
          </label>
        }
      >
        {rivers.data && (
          <div className="grid-row grid-gap-2 margin-bottom-2">
            {rivers.data.map((r) => (
              <div key={r.river_code} className="tablet:grid-col">
                <button
                  type="button"
                  className={`emt-stat emt-stat--button width-full text-left ${r.river_code === river ? "emt-stat--active" : ""}`}
                  onClick={() => setRiver(r.river_code)}
                >
                  <div className="emt-stat__label">{r.river_name ?? r.river_code}</div>
                  <div className="emt-stat__value">{int(r.locks)} locks</div>
                  <div className="emt-stat__hint">
                    {int(r.pending_arrivals)} queued · {dec1(r.avg_delay_24h_min)} min avg delay
                  </div>
                </button>
              </div>
            ))}
          </div>
        )}
        {locks.isPending && <Loading what="locks" />}
        {locks.error && <ErrorBox error={locks.error} />}
        {locks.data && (
          <div className="usa-table-container--scrollable" tabIndex={0}>
            <table className="usa-table usa-table--compact usa-table--striped width-full font-body-2xs">
              <thead>
                <tr>
                  <th scope="col">Lock</th>
                  <th scope="col" className="text-right">Mile</th>
                  <th scope="col">Reading</th>
                  <th scope="col" className="text-right">Upper gage</th>
                  <th scope="col" className="text-right">Lower gage</th>
                  <th scope="col" className="text-right">Queued</th>
                  <th scope="col" className="text-right">Locking</th>
                  <th scope="col" className="text-right">Up 24h</th>
                  <th scope="col" className="text-right">Down 24h</th>
                  <th scope="col" className="text-right">Avg delay</th>
                </tr>
              </thead>
              <tbody>
                {locks.data.map((l) => (
                  <tr key={l.observation_id}>
                    <td>
                      {l.lock_name} <span className="text-base">#{l.lock_number}</span>
                    </td>
                    <td className="text-right">{dec1(l.lock_mile)}</td>
                    <td className="text-no-wrap">{when(l.reading_at)}</td>
                    <td className="text-right">{dec1(l.upper_gage_ft)}</td>
                    <td className="text-right">{dec1(l.lower_gage_ft)}</td>
                    <td className="text-right">{int(l.pending_arrivals)}</td>
                    <td className="text-right">{int(l.locking_now)}</td>
                    <td className="text-right">{int(l.locked_up_24h)}</td>
                    <td className="text-right">{int(l.locked_down_24h)}</td>
                    <td className="text-right">{dec1(l.avg_delay_24h_min)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <div className="grid-row grid-gap-2">
        <div className="desktop:grid-col-7">
          <Section title="Navigation notices in your scope" aside="NTNI by district">
            {notices.isPending && <Loading what="notices" />}
            {notices.error && <ErrorBox error={notices.error} />}
            {notices.data && (
              <ul className="usa-list usa-list--unstyled font-body-2xs">
                {notices.data.map((n) => (
                  <li key={n.notice_no} className="border-bottom border-base-lighter padding-y-05">
                    <a className="usa-link" href={n.notice_url ?? "#"} target="_blank" rel="noreferrer">
                      {n.notice_no}
                    </a>{" "}
                    {n.org_code && <OrgLink code={n.org_code} />} — {n.waterways}{" "}
                    <span className="text-base">· issued {when(n.issue_date)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Section>
        </div>
        <div className="desktop:grid-col-5">
          <Section title="Workforce" aside="EMS labor-log proxy">
            {workforce.isPending && <Loading what="workforce" />}
            {workforce.error && <ErrorBox error={workforce.error} />}
            {workforce.data && (
              <>
                <ProxyBanner>{workforce.data.caveat}</ProxyBanner>
                <div className="grid-row grid-gap-1 margin-bottom-1">
                  <div className="grid-col-6">
                    <Stat
                      label={`FY${workforce.data.fiscal_year} personnel obligations`}
                      value={`$${dec1(workforce.data.personnel_obligated / 1e9)}B`}
                    />
                  </div>
                  <div className="grid-col-6">
                    <Stat
                      label="Share of all obligations"
                      value={workforce.data.personnel_share == null ? "—" : `${dec1(workforce.data.personnel_share * 100)}%`}
                    />
                  </div>
                </div>
                <table className="usa-table usa-table--compact usa-table--striped width-full font-body-2xs">
                  <tbody>
                    {workforce.data.personnel_object_classes.map((o) => (
                      <tr key={o.name}>
                        <td>{o.name}</td>
                        <td className="text-right">${dec1((o.obligated ?? 0) / 1e6)}M</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </Section>
        </div>
      </div>
    </>
  );
}
