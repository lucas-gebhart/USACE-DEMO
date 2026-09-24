import { Link } from "react-router-dom";
import { useFlip, useMigration } from "../lib/migration";
import { ErrorBox, Loading, Section } from "../components/ui";
import { useAuth } from "../lib/auth";

const DIAGRAM = `  BEFORE (one APEX app, 4 pages)              AFTER (page by page)
  ┌──────────────────────────────┐            ┌──────────────────────────────┐
  │ ORDS ─► APEX app 100         │            │ React + USWDS  (/, /orgs, …) │
  │  p1 Dashboard  p2 Districts  │  ───────►  │        │  fetch /v1/*         │
  │  p4 Locks  p5 Project Detail │  strangler │ FastAPI (typed, versioned)   │
  │  session state · PL/SQL procs│    fig     │        │  python-oracledb     │
  └──────────────┬───────────────┘            └────────┬─────────────────────┘
                 │                                     │
                 └───────────►  Oracle 23ai  ◄─────────┘
                        same tables · same emt_legacy package
  The migration_routes table decides, per page, which side the user sees.`;

export default function Migration() {
  const { user } = useAuth();
  const m = useMigration();
  const flip = useFlip();
  if (m.isPending) return <Loading what="migration_routes" />;
  if (m.error) return <ErrorBox error={m.error} />;
  const s = m.data;
  const pct = Math.round((100 * s.migrated_count) / Math.max(1, s.total_count));
  const canFlip = user?.role === "HQ";

  return (
    <>
      <h1 className="font-heading-xl margin-y-0">Migration control</h1>
      <p className="text-base-dark margin-top-05">
        One row per legacy APEX page. Flip a row and the React shell starts rendering the rewritten page in place of the
        embedded APEX page — against the same Oracle tables, no data move. Flip it back and APEX is live again.
        {!canFlip && <> Sign in as an HQ persona to change ownership.</>}
      </p>

      <div className="emt-progress margin-y-3" aria-label="Migration progress">
        <div className="emt-progress__bar" style={{ width: `${pct}%` }} />
        <span className="emt-progress__label">
          {s.migrated_count} of {s.total_count} pages on React + FastAPI ({pct}%)
        </span>
      </div>

      <Section title="Pages">
        <table className="usa-table usa-table--compact usa-table--striped width-full font-body-2xs emt-table-fixed">
          <thead>
            <tr>
              <th scope="col">Page</th>
              <th scope="col">Legacy (APEX app {s.apex_app_id})</th>
              <th scope="col">New (React → FastAPI)</th>
              <th scope="col">Live today</th>
              <th scope="col">What changes</th>
              <th scope="col" className="width-card-lg">
                Action
              </th>
            </tr>
          </thead>
          <tbody>
            {s.routes.map((r) => (
              <tr key={r.route_key}>
                <td>
                  <strong>{r.title}</strong>
                </td>
                <td>
                  <a className="usa-link" href={r.apex_url} target="_blank" rel="noreferrer">
                    page {r.apex_page_id} “{r.apex_page_name}”
                  </a>
                </td>
                <td>
                  <Link className="usa-link" to={r.react_path.replace(":code", user?.org_code ?? "HQ").replace(":id", "1")}>
                    {r.react_path}
                  </Link>
                  <div className="text-base">{r.api_routes.join(", ")}</div>
                </td>
                <td>
                  {r.implementation === "APEX" ? (
                    <span className="usa-tag emt-pill-apex">APEX</span>
                  ) : (
                    <span className="usa-tag emt-pill-react">REACT</span>
                  )}
                  {r.migrated_at && <div className="text-base">{new Date(r.migrated_at).toLocaleString()}</div>}
                </td>
                <td>{r.note}</td>
                <td>
                  {canFlip && (
                    <button
                      type="button"
                      className={`usa-button usa-button--small margin-0 ${r.implementation === "APEX" ? "" : "usa-button--outline"}`}
                      disabled={flip.isPending}
                      onClick={() =>
                        flip.mutate({
                          routeKey: r.route_key,
                          implementation: r.implementation === "APEX" ? "REACT" : "APEX",
                        })
                      }
                    >
                      {r.implementation === "APEX" ? "Migrate to React →" : "← Roll back to APEX"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {flip.error && <ErrorBox error={flip.error} />}
      </Section>

      <Section title="How the switch works" aside="strangler fig">
        <pre className="emt-code">{DIAGRAM}</pre>
        <ul className="usa-list font-body-2xs">
          <li>
            <code>migration_routes</code> (Oracle) holds <code>implementation = APEX | REACT</code> per page;{" "}
            <code>PUT /v1/migration/{"{route}"}</code> is the only write. Both tiers read the same tables.
          </li>
          <li>
            When a page is on APEX, the React shell embeds the ORDS URL <code>{s.apex_base_url}/f?p=…</code> — users keep
            the legacy UI, session state, and PL/SQL processes for that page only.
          </li>
          <li>
            When it is on React, the page is served from <code>/v1/*</code> with JWT-scoped authorization; the APEX page
            still exists (Builder:{" "}
            <a className="usa-link" href={s.apex_builder_url} target="_blank" rel="noreferrer">
              app {s.apex_app_id}
            </a>
            ) so rollback is one UPDATE.
          </li>
        </ul>
      </Section>
    </>
  );
}
