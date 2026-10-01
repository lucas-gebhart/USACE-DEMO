import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import type { SourceLoad, StatusLabel } from "../lib/api";
import { day, int } from "../lib/format";

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="emt-stat">
      <div className="emt-stat__label">{label}</div>
      <div className="emt-stat__value">{value}</div>
      {hint && <div className="emt-stat__hint">{hint}</div>}
    </div>
  );
}

export function StatusTag({ label }: { label: StatusLabel }) {
  const cls = { GROWING: "bg-green", SHRINKING: "bg-secondary", STEADY: "bg-base", UNKNOWN: "bg-base-lighter text-ink" }[label];
  return <span className={`usa-tag ${cls}`}>{label}</span>;
}

export function ProxyBanner({ children }: { children: ReactNode }) {
  return (
    <div className="usa-alert usa-alert--info usa-alert--slim margin-bottom-2">
      <div className="usa-alert__body">
        <p className="usa-alert__text">{children}</p>
      </div>
    </div>
  );
}

export function Loading({ what = "data" }: { what?: string }) {
  return (
    <p className="text-base-dark padding-y-4" role="status">
      Loading {what} from Oracle via FastAPI…
    </p>
  );
}

export function ErrorBox({ error }: { error: unknown }) {
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <div className="usa-alert usa-alert--error usa-alert--slim" role="alert">
      <div className="usa-alert__body">
        <p className="usa-alert__text">{msg}</p>
      </div>
    </div>
  );
}

export function Section({ title, children, aside }: { title: string; children: ReactNode; aside?: ReactNode }) {
  return (
    <section className="margin-bottom-4">
      <div className="display-flex flex-justify flex-align-baseline margin-bottom-1">
        <h2 className="margin-0 font-heading-lg">{title}</h2>
        {aside && <div className="font-body-2xs text-base">{aside}</div>}
      </div>
      {children}
    </section>
  );
}

export function SourceTable({ sources }: { sources: SourceLoad[] }) {
  return (
    <table className="usa-table usa-table--compact usa-table--striped width-full font-body-2xs">
      <thead>
        <tr>
          <th scope="col">Public source (proxy)</th>
          <th scope="col">Fetched</th>
          <th scope="col">Loaded into Oracle</th>
          <th scope="col" className="text-right">
            Rows
          </th>
          <th scope="col">Note</th>
        </tr>
      </thead>
      <tbody>
        {sources.map((s) => (
          <tr key={s.load_id}>
            <td>
              <a className="usa-link" href={s.source_url} target="_blank" rel="noreferrer">
                {s.source}
              </a>
            </td>
            <td>{day(s.fetched_on)}</td>
            <td>{day(s.loaded_at)}</td>
            <td className="text-right">{int(s.row_count)}</td>
            <td>{s.note}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function OrgLink({ code, name }: { code: string; name?: string | null }) {
  return (
    <Link className="usa-link" to={`/orgs/${code}`}>
      {name ?? code}
    </Link>
  );
}
