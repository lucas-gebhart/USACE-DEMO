-- Canonical EMT-style read model. Oracle stays the system of record; the APEX
-- page logic is what moves out. Statements are separated by a line holding
-- only "/" so the file runs unchanged in SQL*Plus, SQLcl, and api/app/migrate.py.

CREATE TABLE organizations (
  code          VARCHAR2(8)   PRIMARY KEY,
  name          VARCHAR2(80)  NOT NULL,
  kind          VARCHAR2(10)  NOT NULL CHECK (kind IN ('HQ', 'DIVISION', 'DISTRICT')),
  parent_code   VARCHAR2(8)   REFERENCES organizations (code),
  dodaac_prefix VARCHAR2(6),
  nid_owner_name VARCHAR2(80),
  states        VARCHAR2(60)
)
/
CREATE TABLE source_loads (
  load_id      NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source       VARCHAR2(60)   NOT NULL,
  source_url   VARCHAR2(400)  NOT NULL,
  fetched_on   DATE           NOT NULL,
  loaded_at    TIMESTAMP      DEFAULT SYSTIMESTAMP NOT NULL,
  row_count    NUMBER         NOT NULL,
  note         VARCHAR2(400)
)
/
CREATE TABLE agency_budget_years (
  fiscal_year          NUMBER(4)  PRIMARY KEY,
  budgetary_resources  NUMBER(18, 2),
  obligations          NUMBER(18, 2),
  outlays              NUMBER(18, 2),
  load_id              NUMBER REFERENCES source_loads (load_id)
)
/
CREATE TABLE agency_obligations_by_period (
  fiscal_year  NUMBER(4)  NOT NULL REFERENCES agency_budget_years (fiscal_year),
  period       NUMBER(2)  NOT NULL,
  obligated    NUMBER(18, 2),
  PRIMARY KEY (fiscal_year, period)
)
/
CREATE TABLE federal_accounts (
  account_code   VARCHAR2(12)  NOT NULL,
  fiscal_year    NUMBER(4)     NOT NULL,
  name           VARCHAR2(160) NOT NULL,
  obligated      NUMBER(18, 2),
  gross_outlays  NUMBER(18, 2),
  load_id        NUMBER REFERENCES source_loads (load_id),
  PRIMARY KEY (account_code, fiscal_year)
)
/
CREATE TABLE program_activities (
  fiscal_year    NUMBER(4)     NOT NULL,
  name           VARCHAR2(160) NOT NULL,
  obligated      NUMBER(18, 2),
  gross_outlays  NUMBER(18, 2),
  PRIMARY KEY (fiscal_year, name)
)
/
CREATE TABLE object_classes (
  fiscal_year    NUMBER(4)     NOT NULL,
  name           VARCHAR2(160) NOT NULL,
  obligated      NUMBER(18, 2),
  gross_outlays  NUMBER(18, 2),
  PRIMARY KEY (fiscal_year, name)
)
/
CREATE TABLE projects (
  project_id            NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name                  VARCHAR2(200) NOT NULL,
  state                 VARCHAR2(40),
  org_code              VARCHAR2(8)   REFERENCES organizations (code),
  division_name         VARCHAR2(80),
  district_name         VARCHAR2(80),
  authorization         VARCHAR2(2000),
  description           VARCHAR2(4000),
  fy2023_allocation     NUMBER(14),
  fy2024_assumed        NUMBER(14),
  fy2024_iija           NUMBER(14),
  fy2025_maintenance    NUMBER(14),
  fy2025_operations     NUMBER(14),
  fy2025_total          NUMBER(14),
  source_page           NUMBER(5),
  load_id               NUMBER REFERENCES source_loads (load_id)
)
/
CREATE TABLE project_business_lines (
  project_id     NUMBER      NOT NULL REFERENCES projects (project_id) ON DELETE CASCADE,
  business_line  VARCHAR2(3) NOT NULL CHECK (business_line IN ('ENS', 'FRM', 'HYD', 'NAV', 'REC', 'WTR')),
  amount         NUMBER(14)  NOT NULL,
  PRIMARY KEY (project_id, business_line)
)
/
CREATE TABLE contracts (
  piid            VARCHAR2(30)  PRIMARY KEY,
  org_code        VARCHAR2(8)   REFERENCES organizations (code),
  recipient_name  VARCHAR2(200),
  description     VARCHAR2(4000),
  start_date      DATE,
  end_date        DATE,
  award_amount    NUMBER(16, 2),
  total_outlays   NUMBER(16, 2),
  award_type      VARCHAR2(60),
  pop_state       VARCHAR2(2),
  naics_code      VARCHAR2(6),
  naics_desc      VARCHAR2(200),
  psc_code        VARCHAR2(4),
  psc_desc        VARCHAR2(200),
  usaspending_id  VARCHAR2(120),
  load_id         NUMBER REFERENCES source_loads (load_id)
)
/
CREATE INDEX contracts_org_ix ON contracts (org_code)
/
CREATE TABLE assets (
  nid_id             VARCHAR2(20)  PRIMARY KEY,
  name               VARCHAR2(200) NOT NULL,
  org_code           VARCHAR2(8)   REFERENCES organizations (code),
  owner_names        VARCHAR2(400),
  primary_owner_type VARCHAR2(40),
  primary_purpose    VARCHAR2(60),
  purposes           VARCHAR2(200),
  latitude           NUMBER(10, 6),
  longitude          NUMBER(10, 6),
  state              VARCHAR2(40),
  county             VARCHAR2(80),
  river              VARCHAR2(120),
  dam_type           VARCHAR2(60),
  nid_height_ft      NUMBER(8, 1),
  dam_length_ft      NUMBER(10, 1),
  year_completed     NUMBER(4),
  nid_storage_af     NUMBER(14, 1),
  drainage_sq_mi     NUMBER(12, 2),
  lock_count         NUMBER(3),
  last_inspection    DATE,
  inspection_freq_yr NUMBER(3),
  hazard             VARCHAR2(20),
  condition          VARCHAR2(20),
  condition_date     DATE,
  eap_status         VARCHAR2(20),
  website_url        VARCHAR2(400),
  load_id            NUMBER REFERENCES source_loads (load_id)
)
/
CREATE INDEX assets_org_ix ON assets (org_code)
/
CREATE INDEX assets_state_ix ON assets (state)
/
CREATE TABLE lock_observations (
  observation_id        NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  river_code            VARCHAR2(4)   NOT NULL,
  river_name            VARCHAR2(80),
  lock_number           VARCHAR2(6)   NOT NULL,
  lock_name             VARCHAR2(80),
  lock_mile             NUMBER(7, 1),
  reading_at            TIMESTAMP,
  upper_gage_ft         NUMBER(9, 2),
  lower_gage_ft         NUMBER(9, 2),
  pending_arrivals      NUMBER(5),
  locking_now           NUMBER(5),
  locked_up_24h         NUMBER(5),
  locked_down_24h       NUMBER(5),
  avg_delay_24h_min     NUMBER(8, 1),
  notes                 VARCHAR2(2000),
  load_id               NUMBER REFERENCES source_loads (load_id)
)
/
CREATE TABLE nav_notices (
  notice_no      VARCHAR2(20)  PRIMARY KEY,
  org_code       VARCHAR2(8)   REFERENCES organizations (code),
  control_number NUMBER,
  issue_date     TIMESTAMP,
  begin_date     TIMESTAMP,
  waterways      VARCHAR2(400),
  notice_url     VARCHAR2(400),
  load_id        NUMBER REFERENCES source_loads (load_id)
)
/
CREATE OR REPLACE VIEW v_org_rollup AS
  SELECT o.code,
         o.name,
         o.kind,
         o.parent_code,
         o.dodaac_prefix,
         o.states,
         (SELECT COUNT(*)              FROM projects  p WHERE p.org_code = o.code)  AS project_count,
         (SELECT NVL(SUM(p.fy2025_total), 0) FROM projects p WHERE p.org_code = o.code) AS fy2025_budget,
         (SELECT COUNT(*)              FROM contracts c WHERE c.org_code = o.code)  AS contract_count,
         (SELECT NVL(SUM(c.award_amount), 0) FROM contracts c WHERE c.org_code = o.code) AS contract_value,
         (SELECT NVL(SUM(c.total_outlays), 0) FROM contracts c WHERE c.org_code = o.code) AS contract_outlays,
         (SELECT COUNT(*)              FROM assets a WHERE a.org_code = o.code)     AS asset_count,
         (SELECT COUNT(*)              FROM nav_notices n WHERE n.org_code = o.code) AS notice_count
  FROM organizations o
/
