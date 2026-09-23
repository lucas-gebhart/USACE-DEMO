import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import type { Implementation } from "../lib/api";
import { apexPageUrl, useFlip, useMigration } from "../lib/migration";
import { useAuth } from "../lib/auth";
import { ErrorBox, Loading } from "../components/ui";

type View = "live" | "apex" | "react" | "split";

export function ApexFrame({ src, title, height = 900 }: { src: string; title: string; height?: number }) {
  return (
    <div className="emt-apex-frame">
      <div className="emt-apex-frame__chrome font-mono-2xs">
        <span className="emt-apex-frame__dot" />
        <span className="emt-apex-frame__dot" />
        <span className="emt-apex-frame__dot" />
        <span className="margin-left-1 text-base-dark">{src}</span>
        <a className="usa-link margin-left-auto" href={src} target="_blank" rel="noreferrer">
          open in new tab ↗
        </a>
      </div>
      <iframe src={src} title={title} style={{ height }} className="emt-apex-frame__iframe" />
    </div>
  );
}

function Pill({ impl }: { impl: Implementation }) {
  return impl === "APEX" ? (
    <span className="usa-tag emt-pill-apex">LEGACY · Oracle APEX</span>
  ) : (
    <span className="usa-tag emt-pill-react">MIGRATED · React + FastAPI</span>
  );
}

export default function MigratedRoute({
  routeKey,
  apexItems,
  children,
}: {
  routeKey: string;
  apexItems?: Record<string, string | number>;
  children: ReactNode;
}) {
  const { user } = useAuth();
  const m = useMigration();
  const flip = useFlip();
  const [view, setView] = useState<View>("live");

  if (m.isPending) return <Loading what="page ownership (migration_routes)" />;
  if (m.error) return <ErrorBox error={m.error} />;
  const route = m.data.routes.find((r) => r.route_key === routeKey);
  if (!route) return <>{children}</>;

  const live = route.implementation;
  const showing: Exclude<View, "live"> = view === "live" ? (live === "APEX" ? "apex" : "react") : view;
  const src = apexPageUrl(route, apexItems);
  const canFlip = user?.role === "HQ";

  const target: Implementation = live === "APEX" ? "REACT" : "APEX";
  const flipLabel = live === "APEX" ? `Migrate to React →` : `← Roll back to APEX`;

  return (
    <div className={`emt-route emt-route--${live.toLowerCase()}`}>
      <div className="emt-route__bar">
        <div className="display-flex flex-align-center flex-wrap">
          <Pill impl={live} />
          <span className="margin-left-1 font-body-2xs text-base-dark">
            {live === "APEX" ? (
              <>
                APEX app {m.data.apex_app_id} · page {route.apex_page_id} “{route.apex_page_name}” · ORDS PL/SQL gateway
              </>
            ) : (
              <>
                {route.api_routes.join(" · ")} · was APEX page {route.apex_page_id}
                {route.migrated_at && <> · migrated {new Date(route.migrated_at).toLocaleString()}</>}
              </>
            )}
          </span>
        </div>
        <div className="display-flex flex-align-center">
          <div className="usa-button-group usa-button-group--segmented margin-0" role="group" aria-label="View">
            {(
              [
                ["live", "Live"],
                ["apex", "APEX"],
                ["react", "React"],
                ["split", "Side by side"],
              ] as [View, string][]
            ).map(([v, label]) => (
              <div className="usa-button-group__item" key={v}>
                <button
                  type="button"
                  className={`usa-button usa-button--outline ${view === v ? "emt-seg-active" : ""}`}
                  onClick={() => setView(v)}
                >
                  {label}
                </button>
              </div>
            ))}
          </div>
          {canFlip && (
            <button
              type="button"
              className={`usa-button margin-left-2 margin-right-0 ${live === "APEX" ? "" : "usa-button--secondary"}`}
              disabled={flip.isPending}
              onClick={() => {
                setView("live");
                flip.mutate({ routeKey, implementation: target });
              }}
            >
              {flip.isPending ? "Updating migration_routes…" : flipLabel}
            </button>
          )}
          <Link className="usa-link font-body-2xs margin-left-2" to="/migration">
            all pages
          </Link>
        </div>
      </div>

      {showing === "apex" && <ApexFrame src={src} title={`Legacy APEX: ${route.title}`} />}
      {showing === "react" && <div className="emt-route__react">{children}</div>}
      {showing === "split" && (
        <div className="grid-row grid-gap-2 emt-split">
          <div className="grid-col-6">
            <p className="emt-split__label emt-split__label--apex">BEFORE · Oracle APEX page {route.apex_page_id}</p>
            <ApexFrame src={src} title={`Legacy APEX: ${route.title}`} height={1400} />
          </div>
          <div className="grid-col-6">
            <p className="emt-split__label emt-split__label--react">AFTER · React + FastAPI {route.react_path}</p>
            <div className="emt-route__react emt-split__react">{children}</div>
          </div>
        </div>
      )}
    </div>
  );
}
