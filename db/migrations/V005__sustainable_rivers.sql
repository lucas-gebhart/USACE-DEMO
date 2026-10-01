-- Public-value read model for the Sustainable Rivers Program (SRP): program footprint over
-- time, river miles by phase / action purpose, and the site roster joined to the org tree.
-- Figures are transcribed from public HEC/ERDC publications (data/fixtures/srp), not GIS.

CREATE TABLE srp_footprint (
  snapshot_key          VARCHAR2(20)  PRIMARY KEY,
  as_of_year            NUMBER(4)     NOT NULL,
  as_of_label           VARCHAR2(80)  NOT NULL,
  rivers                NUMBER(5),
  rivers_qualifier      VARCHAR2(2),
  river_miles           NUMBER(8),
  river_miles_qualifier VARCHAR2(2),
  reservoirs            NUMBER(5),
  reservoirs_qualifier  VARCHAR2(2),
  districts             NUMBER(3),
  divisions             NUMBER(2),
  floodplain_acres      NUMBER(9),
  basis                 VARCHAR2(400),
  source                VARCHAR2(40)  NOT NULL,
  source_url            VARCHAR2(400),
  load_id               NUMBER REFERENCES source_loads (load_id)
)
/
CREATE TABLE srp_metrics (
  metric_id    NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  metric_group VARCHAR2(30)  NOT NULL,
  metric_key   VARCHAR2(40)  NOT NULL,
  label        VARCHAR2(80)  NOT NULL,
  metric_value NUMBER(12, 2) NOT NULL,
  unit         VARCHAR2(20)  NOT NULL,
  qualifier    VARCHAR2(2),
  sort_order   NUMBER(5)     NOT NULL,
  as_of_label  VARCHAR2(80),
  as_of_year   NUMBER(4),
  note         VARCHAR2(400),
  source       VARCHAR2(40)  NOT NULL,
  load_id      NUMBER REFERENCES source_loads (load_id),
  CONSTRAINT srp_metrics_uk UNIQUE (metric_group, metric_key)
)
/
CREATE TABLE srp_sites (
  site_id          NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  site_name        VARCHAR2(80)  NOT NULL,
  river_name       VARCHAR2(60)  NOT NULL,
  action_type      VARCHAR2(30),
  org_code         VARCHAR2(8)   REFERENCES organizations (code),
  co_org_codes     VARCHAR2(40),
  states           VARCHAR2(40),
  infrastructure   VARCHAR2(12),
  structures       VARCHAR2(120),
  start_year       NUMBER(4)     NOT NULL,
  implement_year   NUMBER(4),
  incorporate_year NUMBER(4),
  orgs_engaged     NUMBER(3),
  note             VARCHAR2(400),
  source           VARCHAR2(40)  NOT NULL,
  load_id          NUMBER REFERENCES source_loads (load_id)
)
/
-- Phase today is the furthest phase with a reported year (Incorporate > Implement > Advance).
CREATE OR REPLACE VIEW v_emt_srp_sites AS
  SELECT s.site_id,
         s.site_name,
         s.river_name,
         s.action_type,
         s.org_code,
         d.name                AS district_name,
         d.parent_code         AS division_code,
         v.name                AS division_name,
         s.co_org_codes,
         s.states,
         s.infrastructure,
         CASE s.infrastructure
           WHEN 'Gen'        THEN 'Multipurpose reservoir'
           WHEN 'LD'         THEN 'Lock and dam'
           WHEN 'DD'         THEN 'Dry dam'
           WHEN 'Gen and LD' THEN 'Reservoir + lock and dam'
           ELSE 'Program / multiple'
         END                   AS infrastructure_label,
         s.structures,
         s.start_year,
         s.implement_year,
         s.incorporate_year,
         CASE
           WHEN s.incorporate_year IS NOT NULL THEN 'Incorporate'
           WHEN s.implement_year   IS NOT NULL THEN 'Implement'
           ELSE 'Advance'
         END                   AS phase,
         s.orgs_engaged,
         s.note,
         s.source
    FROM srp_sites s
    LEFT JOIN organizations d ON d.code = s.org_code
    LEFT JOIN organizations v ON v.code = d.parent_code
/
CREATE OR REPLACE VIEW v_emt_srp_action_miles AS
  SELECT label, metric_value AS river_miles, sort_order, as_of_label
    FROM srp_metrics
   WHERE metric_group = 'ACTION_PURPOSE_MILES'
/
CREATE OR REPLACE VIEW v_emt_srp_phase_miles AS
  SELECT label, metric_value AS river_miles, sort_order, as_of_label, note
    FROM srp_metrics
   WHERE metric_group = 'PHASE_MILES'
/
INSERT INTO migration_routes (route_key, title, sort_order, apex_page_id, apex_page_name, react_path, api_routes, note) VALUES
  ('public_value', 'Public value (Sustainable Rivers)', 5, 6, 'Sustainable Rivers', '/public-value', '/v1/public-value/srp',
   'APEX: 2 JET charts + interactive report over v_emt_srp_* views. React: one /v1/public-value/srp response with footprint history, miles by phase/purpose, and the org-scoped site roster.')
/
