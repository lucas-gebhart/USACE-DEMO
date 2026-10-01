import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, type OrgRollup } from "../lib/api";
import { useAuth } from "../lib/auth";
import { BUSINESS_LINES, int, money, moneyCompact, dec1, when } from "../lib/format";
import { ErrorBox, Loading, OrgLink, ProxyBanner, Section, Stat } from "../components/ui";

const COLORS = ["#005ea2", "#00a91c", "#e5a000", "#d83933", "#8168b3", "#0081a1", "#71767a"];

export default function Enterprise() {
  const { user } = useAuth();
  const q = useQuery({ queryKey: ["portfolio", user?.username], queryFn: api.portfolio });
  if (q.isPending) return <Loading what="portfolio" />;
  if (q.error) return <ErrorBox error={q.error} />;
  const p = q.data;
  const fy25 = p.budget_years.find((y) => y.fiscal_year === 2025);
  const years = [...p.budget_years].sort((a, b) => a.fiscal_year - b.fiscal_year).slice(-6);

  return (
    <>
      <h1 className="font-heading-xl margin-bottom-0">
        {p.scope.kind === "HQ" ? "Enterprise" : p.scope.name} portfolio
      </h1>
      <p className="text-base-dark margin-top-05">
        Scope comes from the <code>org</code> claim in your token — {user?.role} at {p.scope.code}. Rollups are read from
        Oracle view <code>v_org_rollup</code>.
      </p>

      <div className="grid-row grid-gap-2 margin-bottom-3">
        <div className="tablet:grid-col">
          <Stat label="FY25 O&M projects" value={int(p.rollup.project_count)} hint="J-sheets (P2 proxy)" />
        </div>
        <div className="tablet:grid-col">
          <Stat label="FY25 O&M budget" value={moneyCompact(p.rollup.fy2025_budget)} hint="justification sheets" />
        </div>
        <div className="tablet:grid-col">
          <Stat label="Contract awards" value={int(p.rollup.contract_count)} hint={moneyCompact(p.rollup.contract_value) + " obligated (CEFMS proxy)"} />
        </div>
        <div className="tablet:grid-col">
          <Stat label="USACE-owned dams" value={int(p.rollup.asset_count)} hint="NID owner match (BUILDER proxy)" />
        </div>
        <div className="tablet:grid-col">
          <Stat
            label="Locks reporting"
            value={int(p.lock_summary.locks_reporting)}
            hint={`${dec1(p.lock_summary.avg_delay_24h_min)} min avg delay · ${when(p.lock_summary.latest_reading)}`}
          />
        </div>
      </div>

      {p.scope.kind === "HQ" && fy25 && (
        <Section title="Civil Works financial execution (USAspending, agency 096)" aside="CEFMS proxy — agency level only">
          <ProxyBanner>
            USAspending publishes agency-level budgetary resources, obligations and outlays. Project-level execution lives
            in CEFMS inside the enclave; this is the public shape of the same money.
          </ProxyBanner>
          <div className="grid-row grid-gap-2">
            <div className="tablet:grid-col-4">
              <Stat label={`FY${fy25.fiscal_year} budgetary resources`} value={moneyCompact(fy25.budgetary_resources)} />
              <Stat label="Obligations" value={moneyCompact(fy25.obligations)} />
              <Stat label="Outlays" value={moneyCompact(fy25.outlays)} />
            </div>
            <div className="tablet:grid-col-8">
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={years} margin={{ left: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="fiscal_year" />
                  <YAxis tickFormatter={(v: number) => moneyCompact(v)} width={70} />
                  <Tooltip formatter={(v) => money(Number(v))} />
                  <Legend />
                  <Bar dataKey="budgetary_resources" name="Budgetary resources" fill={COLORS[0]} />
                  <Bar dataKey="obligations" name="Obligations" fill={COLORS[1]} />
                  <Bar dataKey="outlays" name="Outlays" fill={COLORS[2]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <details className="margin-top-1">
            <summary className="font-body-2xs text-base">Federal accounts &amp; program activities, FY{fy25.fiscal_year}</summary>
            <div className="grid-row grid-gap-2">
              <div className="tablet:grid-col-6">
                <table className="usa-table usa-table--compact usa-table--striped width-full font-body-2xs">
                  <thead>
                    <tr>
                      <th scope="col">Federal account</th>
                      <th scope="col" className="text-right">Obligated</th>
                    </tr>
                  </thead>
                  <tbody>
                    {p.federal_accounts.slice(0, 8).map((a) => (
                      <tr key={a.account_code}>
                        <td>
                          {a.account_code} {a.name}
                        </td>
                        <td className="text-right">{moneyCompact(a.obligated)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="tablet:grid-col-6">
                <table className="usa-table usa-table--compact usa-table--striped width-full font-body-2xs">
                  <thead>
                    <tr>
                      <th scope="col">Program activity</th>
                      <th scope="col" className="text-right">Obligated</th>
                    </tr>
                  </thead>
                  <tbody>
                    {p.program_activities.slice(0, 8).map((a) => (
                      <tr key={a.name}>
                        <td>{a.name}</td>
                        <td className="text-right">{moneyCompact(a.obligated)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </details>
        </Section>
      )}

      <div className="grid-row grid-gap-2">
        <div className="desktop:grid-col-6">
          <Section title="FY25 O&M by business line" aside="J-sheet program codes">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
                <Pie
                  data={p.business_line_mix.map((b) => ({ ...b, name: BUSINESS_LINES[b.business_line] ?? b.business_line }))}
                  dataKey="amount"
                  nameKey="name"
                  innerRadius={45}
                  outerRadius={80}
                  isAnimationActive={false}
                  label={(e) => moneyCompact(Number(e.value))}
                  labelLine={false}
                >
                  {p.business_line_mix.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => money(Number(v))} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </Section>
        </div>
        <div className="desktop:grid-col-6">
          <Section title="Dam hazard / condition (NID)" aside={
              p.scope.kind === "HQ"
                ? "all loaded NID dams: USACE-owned + high-hazard regional context · BUILDER SMS proxy"
                : "USACE-owned dams in scope · BUILDER SMS proxy"
            }>
            <div className="grid-row grid-gap-1">
              <div className="grid-col-6">
                <MixTable title="Hazard potential" rows={p.hazard_mix} />
              </div>
              <div className="grid-col-6">
                <MixTable title="Condition assessment" rows={p.condition_mix} />
              </div>
            </div>
          </Section>
        </div>
      </div>

      <Section title="Roll-up by organization" aside="click a row to drill down">
        <RollupTable root={p.rollup} />
      </Section>
    </>
  );
}

function MixTable({ title, rows }: { title: string; rows: { label: string; count: number }[] }) {
  const total = rows.reduce((s, r) => s + r.count, 0);
  return (
    <table className="usa-table usa-table--compact width-full font-body-2xs margin-0">
      <caption className="text-left font-body-2xs text-bold">{title}</caption>
      <tbody>
        {rows.map((r) => (
          <tr key={r.label}>
            <td>{r.label}</td>
            <td className="text-right">{int(r.count)}</td>
            <td className="text-right text-base">{total ? Math.round((r.count / total) * 100) : 0}%</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function RollupTable({ root }: { root: OrgRollup }) {
  const rows: { o: OrgRollup; depth: number }[] = [];
  const walk = (o: OrgRollup, depth: number) => {
    rows.push({ o, depth });
    [...o.children].sort((a, b) => b.fy2025_budget - a.fy2025_budget).forEach((c) => walk(c, depth + 1));
  };
  walk(root, 0);
  return (
    <div className="usa-table-container--scrollable" tabIndex={0}>
      <table className="usa-table usa-table--compact usa-table--striped width-full font-body-2xs">
        <thead>
          <tr>
            <th scope="col">Organization</th>
            <th scope="col">Kind</th>
            <th scope="col" className="text-right">Projects</th>
            <th scope="col" className="text-right">FY25 O&M</th>
            <th scope="col" className="text-right">Awards</th>
            <th scope="col" className="text-right">Award value</th>
            <th scope="col" className="text-right">Dams</th>
            <th scope="col" className="text-right">Nav notices</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ o, depth }) => (
            <tr key={o.code}>
              <td style={{ paddingLeft: `${0.5 + depth * 1.25}rem` }}>
                <OrgLink code={o.code} name={`${o.code} · ${o.name}`} />
              </td>
              <td>{o.kind}</td>
              <td className="text-right">{int(o.project_count)}</td>
              <td className="text-right">{moneyCompact(o.fy2025_budget)}</td>
              <td className="text-right">{int(o.contract_count)}</td>
              <td className="text-right">{moneyCompact(o.contract_value)}</td>
              <td className="text-right">{int(o.asset_count)}</td>
              <td className="text-right">{int(o.notice_count)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
