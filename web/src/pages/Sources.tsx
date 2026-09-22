import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { ErrorBox, Loading, Section, SourceTable } from "../components/ui";

const MAP = [
  ["Financial & execution (CEFMS feeds)", "USAspending agency 096 + Army awards by district DoDAAC", "Agency-level resources/obligations/outlays; public contract actions. No CEFMS obligation or disbursement detail."],
  ["Workforce (EMS labor logs)", "USAspending personnel object classes; OPM FedScope offline", "Compensation totals only. No labor hours, no project charging."],
  ["Scheduling & lifecycle (P2 / CMP)", "FY2025 Civil Works O&M justification sheets", "Project list, funding by year and business line. No schedules, milestones or CMP records."],
  ["Infrastructure status (BUILDER SMS)", "National Inventory of Dams", "Hazard, condition and inspection date for USACE-owned dams. No facility condition indices or work items."],
  ["Operations", "Corps Locks (LPMS) and NTNI ORDS feeds", "Live public APEX/ORDS apps run by USACE — the real 'before'."],
];

export default function Sources() {
  const q = useQuery({ queryKey: ["sources"], queryFn: api.sources });
  return (
    <>
      <h1 className="font-heading-xl margin-bottom-0">Data lineage</h1>
      <p className="text-base-dark margin-top-05">
        Every row in Oracle carries a <code>source_load_id</code>. <code>data/fetch.py</code> pulls the public sources;
        <code>python -m loaders</code> writes canonical tables and a <code>source_loads</code> record per file.
      </p>
      <Section title="Domain → public proxy">
        <table className="usa-table usa-table--compact usa-table--striped width-full font-body-2xs">
          <thead>
            <tr>
              <th scope="col">EMT data area (internal system)</th>
              <th scope="col">Public proxy used here</th>
              <th scope="col">What it does not show</th>
            </tr>
          </thead>
          <tbody>
            {MAP.map(([a, b, c]) => (
              <tr key={a}>
                <td>{a}</td>
                <td>{b}</td>
                <td>{c}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>
      <Section title="Latest loads">
        {q.isPending && <Loading what="source loads" />}
        {q.error && <ErrorBox error={q.error} />}
        {q.data && <SourceTable sources={q.data} />}
      </Section>
    </>
  );
}
