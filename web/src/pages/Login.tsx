import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, type DevUser } from "../lib/api";
import { useAuth } from "../lib/auth";
import { ErrorBox, Loading } from "../components/ui";

export default function Login() {
  const { login } = useAuth();
  const users = useQuery({ queryKey: ["dev-users"], queryFn: api.devUsers });
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);

  const pick = async (u: DevUser) => {
    setBusy(u.username);
    setError(null);
    try {
      await login(u.username, "demo");
    } catch (e) {
      setError(e);
      setBusy(null);
    }
  };

  return (
    <main className="grid-container padding-y-6">
      <h1 className="font-heading-xl margin-bottom-1">EMT modernization demo</h1>
      <p className="usa-intro margin-top-0">
        Choose a persona. In production this is a CAC / EAMS-A → OIDC redirect; here a dev IdP issues a JWT whose{" "}
        <code>role</code> and <code>org</code> claims replace APEX session state for authorization.
      </p>
      {users.isPending && <Loading what="personas" />}
      {users.error && <ErrorBox error={users.error} />}
      {error != null && <ErrorBox error={error} />}
      <ul className="usa-card-group">
        {users.data?.map((u) => (
          <li key={u.username} className="usa-card tablet:grid-col-6 desktop:grid-col-3">
            <div className="usa-card__container">
              <div className="usa-card__header">
                <h2 className="usa-card__heading font-heading-md">{u.display_name}</h2>
              </div>
              <div className="usa-card__body">
                <p className="margin-0">
                  <span className="usa-tag">{u.role}</span> <span className="text-base-dark">org {u.org_code}</span>
                </p>
                <p className="font-body-2xs text-base margin-bottom-0">
                  Sees {u.role === "HQ" ? "the whole enterprise" : u.role === "DIVISION" ? "its districts" : "one district"}.
                </p>
              </div>
              <div className="usa-card__footer">
                <button className="usa-button" type="button" disabled={busy !== null} onClick={() => pick(u)}>
                  {busy === u.username ? "Signing in…" : `Sign in as ${u.username}`}
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </main>
  );
}
