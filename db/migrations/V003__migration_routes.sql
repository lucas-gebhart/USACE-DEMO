-- Strangler-fig routing table. One row per user-facing page of the legacy APEX
-- application (APEX app 100, served by ORDS). `implementation` says which tier
-- currently owns the page; the React shell reads it and either embeds the APEX
-- page or renders the rewritten page. Both hit the same Oracle tables, so a
-- page can be flipped back and forth without touching data.

CREATE TABLE migration_routes (
  route_key      VARCHAR2(30)  PRIMARY KEY,
  title          VARCHAR2(80)  NOT NULL,
  sort_order     NUMBER(3)     NOT NULL,
  apex_page_id   NUMBER(6)     NOT NULL,
  apex_page_name VARCHAR2(80)  NOT NULL,
  react_path     VARCHAR2(80)  NOT NULL,
  api_routes     VARCHAR2(400) NOT NULL,
  implementation VARCHAR2(5)   DEFAULT 'APEX' NOT NULL CHECK (implementation IN ('APEX', 'REACT')),
  migrated_at    TIMESTAMP,
  note           VARCHAR2(400)
)
/
INSERT INTO migration_routes (route_key, title, sort_order, apex_page_id, apex_page_name, react_path, api_routes, note) VALUES
  ('enterprise', 'Enterprise dashboard', 1, 1, 'Dashboard', '/', '/v1/portfolio',
   'APEX: 4 JET chart regions, each with its own SQL over v_emt_* views. React: one typed /v1/portfolio response.')
/
INSERT INTO migration_routes (route_key, title, sort_order, apex_page_id, apex_page_name, react_path, api_routes, note) VALUES
  ('org', 'Division / district drill-down', 2, 2, 'Districts', '/orgs/:code', '/v1/orgs/{code}, /v1/projects, /v1/contracts, /v1/assets',
   'APEX: interactive report over v_emt_org_rollup, org chosen by an IR row filter in the URL. React: org-scoped routes, JWT decides visibility.')
/
INSERT INTO migration_routes (route_key, title, sort_order, apex_page_id, apex_page_name, react_path, api_routes, note) VALUES
  ('project', 'Project detail', 3, 5, 'Project Detail', '/projects/:id', '/v1/projects/{id}, /v1/contracts?project_id=',
   'APEX: page items filled by a BEFORE_HEADER PL/SQL page process (emt_legacy.project_status_label) + classic report over CONTRACTS. React: same rule in services.py; /v1/legacy proves equivalence.')
/
INSERT INTO migration_routes (route_key, title, sort_order, apex_page_id, apex_page_name, react_path, api_routes, note) VALUES
  ('ops', 'Operations (locks, notices)', 4, 4, 'Lock Operations', '/ops', '/v1/ops/locks, /v1/ops/notices, /v1/workforce',
   'APEX: interactive report over v_emt_lock_status (LOCK_OBSERVATIONS). React: locks + notices + workforce via /v1/ops.')
/
