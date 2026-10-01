import { useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  LabelList,
  Legend,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, type SrpFootprint, type SrpMetric, type SrpPhase, type SrpSite } from "../lib/api";
import { useAuth } from "../lib/auth";
import { int, pct } from "../lib/format";
import { ErrorBox, Loading, OrgLink, ProxyBanner, Section, SourceTable, Stat } from "../components/ui";

const BLUE = "#005ea2";
const GREEN = "#00a91c";
const GOLD = "#e5a000";
const TEAL = "#0081a1";
const GRAY = "#a9aeb1";
const PHASE_COLORS: Record<SrpPhase, string> = { Advance: TEAL, Implement: GOLD, Incorporate: GREEN };
const MIX_COLORS = [BLUE, GOLD, GREEN, TEAL, "#8168b3", "#71767a"];

/** "90" + ">" or "+" → "90+"; the qualifier records that the source said "more than". */
function qualified(v: number | null | undefined, q: string | null | undefined): string {
  if (v == null) return "—";
  return `${int(v)}${q === ">" || q === "+" ? "+" : ""}`;
}

/** A Recharts figure with an accessible name and an equivalent data table behind a disclosure. */
function Chart({
  title,
  description,
  height = 240,
  children,
  table,
}: {
  title: string;
  description: string;
  height?: number;
  children: ReactNode;
  table: ReactNode;
}) {
  return (
    <figure className="margin-0">
      <div role="img" aria-label={`${title}. ${description}`} style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          {children as never}
        </ResponsiveContainer>
      </div>
      <figcaption className="font-body-2xs text-base-dark margin-top-05">{description}</figcaption>
      <details className="margin-top-05 font-body-2xs">
        <summary className="text-primary">Show data table</summary>
        {table}
      </details>
    </figure>
  );
}

function MetricTable({ rows, caption, valueHeader }: { rows: SrpMetric[]; caption: string; valueHeader: string }) {
  return (
    <table className="usa-table usa-table--compact usa-table--striped width-full">
      <caption className="usa-sr-only">{caption}</caption>
      <thead>
        <tr>
          <th scope="col">Category</th>
          <th scope="col" className="text-right">
            {valueHeader}
          </th>
          <th scope="col">Note</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((m) => (
          <tr key={m.metric_key}>
            <th scope="row">{m.label}</th>
            <td className="text-right text-tabular">{qualified(m.metric_value, m.qualifier)}</td>
            <td>{m.note ?? ""}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function PhasePill({ phase }: { phase: SrpPhase }) {
  return (
    <span className="usa-tag" style={{ background: PHASE_COLORS[phase] }}>
      {phase}
    </span>
  );
}

export default function PublicValue() {
  const { user } = useAuth();
  const q = useQuery({ queryKey: ["public-value-srp", user?.username], queryFn: api.publicValueSrp });
  const isHQ = user?.role === "HQ";
  const [scopeOnly, setScopeOnly] = useState(!isHQ);
  const [phase, setPhase] = useState<SrpPhase | "ALL">("ALL");

  const sites = useMemo(() => {
    const all = q.data?.sites ?? [];
    return all.filter((s) => (!scopeOnly || s.in_scope) && (phase === "ALL" || s.phase === phase));
  }, [q.data, scopeOnly, phase]);

  if (q.isPending) return <Loading what="Sustainable Rivers Program metrics" />;
  if (q.error) return <ErrorBox error={q.error} />;
  const p = q.data;

  const structures = Object.fromEntries(p.structures.map((m) => [m.metric_key, m])) as Record<string, SrpMetric | undefined>;
  const current = p.footprint.reduce((a, b) => (b.as_of_year > a.as_of_year ? b : a));
  const miles = structures.river_miles;
  const usaceMiles = structures.usace_river_miles;
  const share = miles && usaceMiles ? miles.metric_value / usaceMiles.metric_value : null;
  const phaseTotal = p.phase_miles.reduce((n, m) => n + m.metric_value, 0);
  const purposeTotal = p.action_purpose_miles.reduce((n, m) => n + m.metric_value, 0);
  const acresTotal = p.action_purpose_acres.reduce((n, m) => n + m.metric_value, 0);
  const asOf = miles?.as_of_label ?? "";

  const footprintRows = p.footprint.filter((f) => f.rivers != null || f.river_miles != null);
  const phaseRow = Object.fromEntries(p.phase_miles.map((m) => [m.label, m.metric_value])) as Record<string, number>;
  const purposeRows = [...p.action_purpose_miles].sort((a, b) => b.metric_value - a.metric_value);
  const inScopeSites = p.sites.filter((s) => s.in_scope);
  const scopedDivisions = p.by_division.filter((d) => d.in_scope);

  return (
    <>
      <h1 className="font-heading-xl margin-bottom-0">Public value — Sustainable Rivers Program</h1>
      <p className="text-base-dark margin-top-05">
        What changing how USACE operates its dams gives back to the public: river miles with restored environmental
        flows, the reservoirs and lock-and-dam systems involved, and the river systems covered. SRP is a USACE + The
        Nature Conservancy partnership; authorized project purposes are kept while releases and pool levels are tuned
        for ecological benefit.
        {!isHQ && (
          <>
            {" "}
            Your scope ({p.scope.code}) covers <strong>{inScopeSites.length}</strong> of {p.sites.length} program sites.
          </>
        )}
      </p>
      <ProxyBanner>
        Public program reporting, not an internal feed: figures are transcribed from HEC/ERDC In-Progress Reviews, the SRP
        Metrics Framework and the HEC program site (listed under Sources). They are program-reported totals, not a GIS
        measurement, and each snapshot keeps its own reporting date.
      </ProxyBanner>

      <div className="grid-row grid-gap-2 margin-bottom-3">
        <div className="tablet:grid-col">
          <Stat label="River miles" value={qualified(miles?.metric_value, miles?.qualifier)} hint={asOf} />
        </div>
        <div className="tablet:grid-col">
          <Stat
            label="River systems"
            value={qualified(structures.rivers?.metric_value, structures.rivers?.qualifier)}
            hint={asOf}
          />
        </div>
        <div className="tablet:grid-col">
          <Stat
            label="Reservoirs"
            value={qualified(structures.reservoirs?.metric_value, structures.reservoirs?.qualifier)}
            hint="multipurpose dams (Gen)"
          />
        </div>
        <div className="tablet:grid-col">
          <Stat
            label="Lock & dam systems"
            value={qualified(structures.lock_dam_systems?.metric_value, structures.lock_dam_systems?.qualifier)}
            hint="navigation (LD)"
          />
        </div>
        <div className="tablet:grid-col">
          <Stat
            label="Dry dams"
            value={qualified(structures.dry_dams?.metric_value, structures.dry_dams?.qualifier)}
            hint="flood risk (DD)"
          />
        </div>
        <div className="tablet:grid-col">
          <Stat
            label="Districts engaged"
            value={qualified(structures.districts?.metric_value, null)}
            hint={structures.districts?.unit ?? ""}
          />
        </div>
        {share != null && (
          <div className="tablet:grid-col">
            <Stat label="Share of USACE-influenced river miles" value={pct(share)} hint={`of ${int(usaceMiles?.metric_value)} miles`} />
          </div>
        )}
      </div>

      <Section
        title="Program footprint over time"
        aside={`Latest: ${current.as_of_label} — ${qualified(current.rivers, current.rivers_qualifier)} river systems, ${qualified(current.river_miles, current.river_miles_qualifier)} miles${current.floodplain_acres ? `, ${int(current.floodplain_acres)} floodplain acres` : ""}`}
      >
        <Chart
          title="SRP river systems and river miles by reporting point"
          description={`River systems (bars, left axis) and river miles (line, right axis) as reported at each point from ${footprintRows[0]?.as_of_label} to ${current.as_of_label}. Each point is a separate publication's own total; they are not summed.`}
          height={260}
          table={
            <table className="usa-table usa-table--compact usa-table--striped width-full">
              <caption className="usa-sr-only">Program footprint by reporting point</caption>
              <thead>
                <tr>
                  <th scope="col">Reporting point</th>
                  <th scope="col" className="text-right">River systems</th>
                  <th scope="col" className="text-right">River miles</th>
                  <th scope="col" className="text-right">Reservoirs</th>
                  <th scope="col" className="text-right">Districts</th>
                  <th scope="col">Basis</th>
                </tr>
              </thead>
              <tbody>
                {p.footprint.map((f: SrpFootprint) => (
                  <tr key={f.snapshot_key}>
                    <th scope="row">{f.as_of_label}</th>
                    <td className="text-right text-tabular">{qualified(f.rivers, f.rivers_qualifier)}</td>
                    <td className="text-right text-tabular">{qualified(f.river_miles, f.river_miles_qualifier)}</td>
                    <td className="text-right text-tabular">{qualified(f.reservoirs, f.reservoirs_qualifier)}</td>
                    <td className="text-right text-tabular">{qualified(f.districts, null)}</td>
                    <td>
                      {f.basis}{" "}
                      {f.source_url && (
                        <a href={f.source_url} target="_blank" rel="noreferrer">
                          ({f.source})
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          }
        >
          <ComposedChart data={footprintRows} margin={{ left: 8, right: 8 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="as_of_year" />
            <YAxis yAxisId="rivers" width={40} allowDecimals={false} />
            <YAxis yAxisId="miles" orientation="right" width={60} tickFormatter={(v: number) => int(v)} />
            <Tooltip
              formatter={(v, name) => [int(Number(v)), String(name)]}
              labelFormatter={(_, payload) => {
                const row = payload?.[0]?.payload as SrpFootprint | undefined;
                return row ? `${row.as_of_label} (${row.source})` : "";
              }}
            />
            <Legend />
            <Bar yAxisId="rivers" dataKey="rivers" name="River systems" fill={BLUE} radius={[3, 3, 0, 0]}>
              <LabelList dataKey="rivers" position="top" formatter={(v) => int(Number(v))} />
            </Bar>
            <Line yAxisId="miles" dataKey="river_miles" name="River miles" stroke={GREEN} strokeWidth={3} dot={{ r: 5 }} connectNulls />
          </ComposedChart>
        </Chart>
      </Section>

      <Section title="Where the river miles are" aside={`${int(phaseTotal)} miles by phase · ${int(purposeTotal)} miles by action purpose`}>
        <div className="grid-row grid-gap-3">
          <div className="tablet:grid-col-5">
            <h3 className="font-heading-sm margin-y-1">By program phase</h3>
            <Chart
              title="SRP river miles by program phase"
              description={`Of ${int(phaseTotal)} river miles (${p.phase_miles[0]?.as_of_label}), ${p.phase_miles.map((m) => `${int(m.metric_value)} are in ${m.label}`).join(", ")}. Advance = defining flow needs; Implement = running e-flows; Incorporate = written into water control manuals.`}
              height={120}
              table={<MetricTable rows={p.phase_miles} caption="River miles by program phase" valueHeader="River miles" />}
            >
              <BarChart data={[{ name: "miles", ...phaseRow }]} layout="vertical" margin={{ left: 8, right: 8 }}>
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="name" hide />
                <Tooltip formatter={(v, name) => [`${int(Number(v))} miles`, String(name)]} />
                <Legend />
                {p.phase_miles.map((m) => (
                  <Bar key={m.metric_key} dataKey={m.label} stackId="a" fill={PHASE_COLORS[m.label as SrpPhase] ?? GRAY} />
                ))}
              </BarChart>
            </Chart>
            <h3 className="font-heading-sm margin-top-3 margin-bottom-1">Floodplain and habitat acres</h3>
            <table className="usa-table usa-table--compact usa-table--striped width-full font-body-2xs">
              <caption className="usa-sr-only">Acres affected by environmental action purpose</caption>
              <thead>
                <tr>
                  <th scope="col">Action purpose</th>
                  <th scope="col" className="text-right">Acres</th>
                </tr>
              </thead>
              <tbody>
                {p.action_purpose_acres.map((m) => (
                  <tr key={m.metric_key}>
                    <th scope="row">{m.label}</th>
                    <td className="text-right text-tabular">{int(m.metric_value)}</td>
                  </tr>
                ))}
                <tr>
                  <th scope="row">Total reported</th>
                  <td className="text-right text-tabular text-bold">{int(acresTotal)}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div className="tablet:grid-col-7">
            <h3 className="font-heading-sm margin-y-1">By environmental action purpose (2002–2023)</h3>
            <Chart
              title="SRP river miles by environmental action purpose"
              description={`Reported maximum river miles affected in a typical implementation year, by purpose: ${purposeRows.map((m) => `${m.label} ${int(m.metric_value)}`).join(", ")}. Purposes overlap, so the ${int(purposeTotal)}-mile total is not the program footprint.`}
              height={320}
              table={<MetricTable rows={p.action_purpose_miles} caption="River miles by action purpose" valueHeader="River miles" />}
            >
              <BarChart data={purposeRows} layout="vertical" margin={{ left: 8, right: 40 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tickFormatter={(v: number) => int(v)} />
                <YAxis type="category" dataKey="label" width={170} tick={{ fontSize: 12 }} />
                <Tooltip formatter={(v) => [`${int(Number(v))} miles`, "River miles"]} />
                <Bar dataKey="metric_value" name="River miles" fill={BLUE} radius={[0, 3, 3, 0]}>
                  <LabelList dataKey="metric_value" position="right" formatter={(v) => int(Number(v))} />
                </Bar>
              </BarChart>
            </Chart>
          </div>
        </div>
      </Section>

      <Section title="Structures and systems covered" aside={`${p.sites.length} sites on ${new Set(p.sites.map((s) => s.river_name)).size} rivers`}>
        <div className="grid-row grid-gap-3">
          <div className="tablet:grid-col-4">
            <h3 className="font-heading-sm margin-y-1">Sites by structure type</h3>
            <Chart
              title="SRP sites by type of structure operated"
              description={p.infrastructure_mix.map((m) => `${m.label}: ${m.count} sites`).join("; ") + "."}
              height={240}
              table={
                <table className="usa-table usa-table--compact usa-table--striped width-full">
                  <caption className="usa-sr-only">Sites by structure type</caption>
                  <thead>
                    <tr>
                      <th scope="col">Structure type</th>
                      <th scope="col" className="text-right">Sites</th>
                    </tr>
                  </thead>
                  <tbody>
                    {p.infrastructure_mix.map((m) => (
                      <tr key={m.label}>
                        <th scope="row">{m.label}</th>
                        <td className="text-right text-tabular">{m.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              }
            >
              <PieChart>
                <Pie data={p.infrastructure_mix} dataKey="count" nameKey="label" innerRadius={50} outerRadius={85} paddingAngle={2} label={(e) => String(e.value)}>
                  {p.infrastructure_mix.map((m, i) => (
                    <Cell key={m.label} fill={MIX_COLORS[i % MIX_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
              </PieChart>
            </Chart>
          </div>
          <div className="tablet:grid-col-8">
            <h3 className="font-heading-sm margin-y-1">
              Sites by division{!isHQ && scopedDivisions.length > 0 && <> — {scopedDivisions.map((d) => d.code).join(", ")} highlighted</>}
            </h3>
            <Chart
              title="SRP sites by USACE division"
              description={p.by_division.map((d) => `${d.name} ${d.sites} sites (${d.implementing} implementing or incorporated)`).join("; ") + "."}
              height={240}
              table={
                <table className="usa-table usa-table--compact usa-table--striped width-full">
                  <caption className="usa-sr-only">Sites by division</caption>
                  <thead>
                    <tr>
                      <th scope="col">Division</th>
                      <th scope="col" className="text-right">Sites</th>
                      <th scope="col" className="text-right">Implementing / incorporated</th>
                    </tr>
                  </thead>
                  <tbody>
                    {p.by_division.map((d) => (
                      <tr key={d.code}>
                        <th scope="row">
                          <OrgLink code={d.code} name={d.name} />
                        </th>
                        <td className="text-right text-tabular">{d.sites}</td>
                        <td className="text-right text-tabular">{d.implementing}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              }
            >
              <BarChart data={p.by_division} margin={{ left: 8, right: 8 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="code" />
                <YAxis allowDecimals={false} width={30} />
                <Tooltip
                  labelFormatter={(code) => p.by_division.find((d) => d.code === code)?.name ?? String(code)}
                />
                <Legend />
                <Bar dataKey="sites" name="Sites engaged" radius={[3, 3, 0, 0]}>
                  {p.by_division.map((d) => (
                    <Cell key={d.code} fill={isHQ || d.in_scope ? BLUE : GRAY} />
                  ))}
                </Bar>
                <Bar dataKey="implementing" name="Implementing / incorporated" radius={[3, 3, 0, 0]}>
                  {p.by_division.map((d) => (
                    <Cell key={d.code} fill={isHQ || d.in_scope ? GREEN : "#c9c9c9"} />
                  ))}
                </Bar>
              </BarChart>
            </Chart>
          </div>
        </div>
      </Section>

      <Section title="Demand from the field" aside="new rivers proposed by districts each year">
        <div className="grid-row grid-gap-3">
          <div className="tablet:grid-col-8">
            <Chart
              title="New rivers proposed for SRP by fiscal year"
              description={`Districts proposed ${p.new_river_proposals.map((m) => `${int(m.metric_value)} rivers in ${m.label}`).join(", ")}.`}
              height={200}
              table={<MetricTable rows={p.new_river_proposals} caption="New rivers proposed by fiscal year" valueHeader="Rivers proposed" />}
            >
              <BarChart data={p.new_river_proposals} margin={{ left: 8, right: 8 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="label" />
                <YAxis allowDecimals={false} width={30} />
                <Tooltip
                  formatter={(v) => [`${int(Number(v))} rivers`, "Proposed"]}
                  labelFormatter={(label) => p.new_river_proposals.find((m) => m.label === label)?.note ?? String(label)}
                />
                <Bar dataKey="metric_value" name="Rivers proposed" fill={TEAL} radius={[3, 3, 0, 0]}>
                  <LabelList dataKey="metric_value" position="top" formatter={(v) => int(Number(v))} />
                </Bar>
              </BarChart>
            </Chart>
          </div>
          <div className="tablet:grid-col-4">
            <p className="font-body-2xs text-base-dark margin-top-1">
              Each year the program asks districts to nominate rivers for new SRP work. Proposals have exceeded available
              funding every year since 2020 (HEC Emerging Sites page); the FY2026 call notes a 56% budget reduction.
              Pipeline interest is one way to show that operational change, not new construction, is what the field is
              asking for.
            </p>
          </div>
        </div>
      </Section>

      <Section
        title="Site roster"
        aside={
          <span className="display-inline-flex flex-align-center">
            <label className="usa-checkbox usa-checkbox--tile margin-0 padding-0" style={{ background: "none", border: "none" }}>
              <input id="srp-scope-only" className="usa-checkbox__input" type="checkbox" checked={scopeOnly} onChange={(e) => setScopeOnly(e.target.checked)} disabled={isHQ} />
              <span className="usa-checkbox__label margin-0 padding-y-0 padding-left-4 font-body-2xs">
                My scope only ({inScopeSites.length})
              </span>
            </label>
            <span className="margin-x-1" aria-hidden="true">
              ·
            </span>
            <label htmlFor="srp-phase" className="margin-right-05">
              Phase
            </label>
            <select id="srp-phase" className="usa-select margin-0 padding-y-05 font-body-2xs" style={{ width: "auto", height: "auto" }} value={phase} onChange={(e) => setPhase(e.target.value as SrpPhase | "ALL")}>
              <option value="ALL">All</option>
              <option value="Advance">Advance</option>
              <option value="Implement">Implement</option>
              <option value="Incorporate">Incorporate</option>
            </select>
          </span>
        }
      >
        <div className="display-flex flex-wrap grid-gap-1 margin-bottom-1 font-body-2xs">
          {p.phase_mix.map((m) => (
            <span key={m.label} className="margin-right-2">
              <PhasePill phase={m.label as SrpPhase} /> {m.count}
            </span>
          ))}
        </div>
        <div className="usa-table-container--scrollable" tabIndex={0}>
          <table className="usa-table usa-table--compact usa-table--striped width-full font-body-2xs">
            <caption className="usa-sr-only">
              Sustainable Rivers Program sites, {sites.length} shown of {p.sites.length}
            </caption>
            <thead>
              <tr>
                <th scope="col">Site</th>
                <th scope="col">District</th>
                <th scope="col">Structure type</th>
                <th scope="col">Structures</th>
                <th scope="col">Action</th>
                <th scope="col" className="text-right">Started</th>
                <th scope="col">Phase</th>
                <th scope="col" className="text-right">Orgs engaged</th>
              </tr>
            </thead>
            <tbody>
              {sites.map((s: SrpSite) => (
                <tr key={s.site_id} className={!isHQ && s.in_scope ? "text-bold" : ""}>
                  <th scope="row">
                    {s.site_name}
                    {s.states && <span className="text-base-dark text-normal"> · {s.states.replaceAll(";", ", ")}</span>}
                  </th>
                  <td>
                    {s.org_code ? <OrgLink code={s.org_code} name={s.district_name} /> : (s.co_org_codes ?? "multiple")}
                    {s.division_code && <span className="text-base-dark text-normal"> · {s.division_code}</span>}
                  </td>
                  <td>{s.infrastructure_label}</td>
                  <td>{s.structures ?? "—"}</td>
                  <td>{s.action_type ?? "—"}</td>
                  <td className="text-right text-tabular">{s.start_year}</td>
                  <td className="text-no-wrap">
                    <PhasePill phase={s.phase} />
                    {(s.incorporate_year ?? s.implement_year) && (
                      <span className="text-base-dark"> since {s.incorporate_year ?? s.implement_year}</span>
                    )}
                  </td>
                  <td className="text-right text-tabular">{s.orgs_engaged ?? "—"}</td>
                </tr>
              ))}
              {sites.length === 0 && (
                <tr>
                  <td colSpan={8}>No sites match this filter.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <p className="font-body-2xs text-base-dark margin-top-1">
          Gen = multipurpose reservoir · LD = lock and dam · DD = dry dam. Start / implement / incorporate years and
          organizations engaged come from Metrics Framework Appendix A; sites listed only in an In-Progress Review carry
          no engagement count.
        </p>
      </Section>

      <Section title="Sources">
        <ul className="usa-list font-body-2xs">
          {p.documents.map((d) => (
            <li key={d.key}>
              <a href={d.url} target="_blank" rel="noreferrer">
                {d.title}
              </a>{" "}
              <code>{d.key}</code>
            </li>
          ))}
        </ul>
        <SourceTable sources={p.sources} />
      </Section>
    </>
  );
}
