import { Navigate, NavLink, Route, Routes, useParams } from "react-router-dom";
import { useAuth } from "./lib/auth";
import Login from "./pages/Login";
import Enterprise from "./pages/Enterprise";
import OrgPage from "./pages/OrgPage";
import ProjectPage from "./pages/ProjectPage";
import Operations from "./pages/Operations";
import Coexistence from "./pages/Coexistence";
import Sources from "./pages/Sources";
import Migration from "./pages/Migration";
import MigratedRoute from "./components/MigratedRoute";

function OrgRoute() {
  const { code = "" } = useParams();
  return (
    <MigratedRoute routeKey="org" apexItems={{ IR_ROWFILTER: code.toUpperCase() }}>
      <OrgPage />
    </MigratedRoute>
  );
}

function ProjectRoute() {
  const { id = "" } = useParams();
  return (
    <MigratedRoute routeKey="project" apexItems={{ P5_PROJECT_ID: id }}>
      <ProjectPage />
    </MigratedRoute>
  );
}

export default function App() {
  const { user, ready, logout } = useAuth();
  if (!ready) return null;
  if (!user) return <Login />;

  const nav = [
    { to: "/", label: "Enterprise" },
    { to: `/orgs/${user.org_code}`, label: user.role === "DISTRICT" ? "My district" : "Drill-down" },
    { to: "/ops", label: "Operations" },
    { to: "/migration", label: "Migration control" },
    { to: "/coexistence", label: "PL/SQL coexistence" },
    { to: "/sources", label: "Data lineage" },
  ];

  return (
    <>
      <a className="usa-skipnav" href="#main">
        Skip to main content
      </a>
      <section className="usa-banner" aria-label="Demo notice">
        <div className="usa-accordion">
          <header className="usa-banner__header">
            <div className="usa-banner__inner">
              <div className="grid-col-fill tablet:grid-col-auto">
                <p className="usa-banner__header-text">
                  Modernization demo — public data only. Nothing here is CEFMS, EMS, P2/CMP, or BUILDER; each source is a
                  labelled proxy. Oracle remains the system of record.
                </p>
              </div>
            </div>
          </header>
        </div>
      </section>
      <header className="usa-header usa-header--basic">
        <div className="usa-nav-container">
          <div className="usa-navbar">
            <div className="usa-logo">
              <em className="usa-logo__text">
                <NavLink to="/">EMT · modernized</NavLink>
              </em>
            </div>
          </div>
          <nav aria-label="Primary navigation" className="usa-nav is-visible">
            <ul className="usa-nav__primary usa-accordion">
              {nav.map((n) => (
                <li key={n.to} className="usa-nav__primary-item">
                  <NavLink to={n.to} end={n.to === "/"} className={({ isActive }) => (isActive ? "usa-current" : "")}>
                    <span>{n.label}</span>
                  </NavLink>
                </li>
              ))}
            </ul>
            <div className="usa-nav__secondary">
              <ul className="usa-nav__secondary-links">
                <li className="usa-nav__secondary-item">
                  <span className="text-base-dark">
                    {user.display_name} · <strong>{user.role}</strong> · {user.org_code}
                  </span>
                </li>
                <li className="usa-nav__secondary-item">
                  <button className="usa-button usa-button--unstyled" type="button" onClick={logout}>
                    Switch persona
                  </button>
                </li>
              </ul>
            </div>
          </nav>
        </div>
      </header>
      <main id="main" className="grid-container-widescreen padding-y-3">
        <Routes>
          <Route
            path="/"
            element={
              <MigratedRoute routeKey="enterprise">
                <Enterprise />
              </MigratedRoute>
            }
          />
          <Route path="/orgs/:code" element={<OrgRoute />} />
          <Route path="/projects/:id" element={<ProjectRoute />} />
          <Route
            path="/ops"
            element={
              <MigratedRoute routeKey="ops">
                <Operations />
              </MigratedRoute>
            }
          />
          <Route path="/migration" element={<Migration />} />
          <Route path="/coexistence" element={<Coexistence />} />
          <Route path="/sources" element={<Sources />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <footer className="usa-footer usa-footer--slim">
        <div className="grid-container-widescreen usa-footer__return-to-top">
          <span className="font-body-2xs text-base">
            React + USWDS → FastAPI → Oracle 23ai Free. APEX-era PL/SQL (<code>emt_legacy</code>) retained for coexistence.
          </span>
        </div>
      </footer>
    </>
  );
}
