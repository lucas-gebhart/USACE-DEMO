-- Views the legacy EMT APEX application (db/apex/f100.sql) reads. They sit on the same
-- canonical tables as the FastAPI service, which is the whole point of the coexistence
-- demo: both UIs query one Oracle read model. Kept here (not in the APEX export) so they
-- are versioned, reviewable, and applied by the same migration runner as everything else.

CREATE OR REPLACE VIEW v_emt_division_rollup AS
  SELECT d.code,
         d.name,
         d.states,
         (SELECT COUNT(*) FROM organizations x WHERE x.parent_code = d.code) AS district_count,
         (SELECT COUNT(*) FROM projects p JOIN organizations o ON o.code = p.org_code
           WHERE o.code = d.code OR o.parent_code = d.code)                    AS project_count,
         (SELECT NVL(SUM(p.fy2025_total), 0) FROM projects p JOIN organizations o ON o.code = p.org_code
           WHERE o.code = d.code OR o.parent_code = d.code)                    AS fy2025_budget,
         (SELECT COUNT(*) FROM contracts c JOIN organizations o ON o.code = c.org_code
           WHERE o.code = d.code OR o.parent_code = d.code)                    AS contract_count,
         (SELECT NVL(SUM(c.award_amount), 0) FROM contracts c JOIN organizations o ON o.code = c.org_code
           WHERE o.code = d.code OR o.parent_code = d.code)                    AS contract_value,
         (SELECT COUNT(*) FROM assets a JOIN organizations o ON o.code = a.org_code
           WHERE o.code = d.code OR o.parent_code = d.code)                    AS asset_count
  FROM organizations d
  WHERE d.kind = 'DIVISION'
/
-- Every organization with hierarchical totals (a division includes its districts, HQ includes all).
CREATE OR REPLACE VIEW v_emt_org_rollup AS
  SELECT o.code,
         o.name,
         o.kind,
         o.parent_code,
         o.dodaac_prefix,
         o.states,
         (SELECT COUNT(*) FROM projects p JOIN organizations x ON x.code = p.org_code
           WHERE o.kind = 'HQ' OR x.code = o.code OR x.parent_code = o.code)       AS project_count,
         (SELECT NVL(SUM(p.fy2025_total), 0) FROM projects p JOIN organizations x ON x.code = p.org_code
           WHERE o.kind = 'HQ' OR x.code = o.code OR x.parent_code = o.code)       AS fy2025_budget,
         (SELECT COUNT(*) FROM contracts c JOIN organizations x ON x.code = c.org_code
           WHERE o.kind = 'HQ' OR x.code = o.code OR x.parent_code = o.code)       AS contract_count,
         (SELECT NVL(SUM(c.award_amount), 0) FROM contracts c JOIN organizations x ON x.code = c.org_code
           WHERE o.kind = 'HQ' OR x.code = o.code OR x.parent_code = o.code)       AS contract_value,
         (SELECT NVL(SUM(c.total_outlays), 0) FROM contracts c JOIN organizations x ON x.code = c.org_code
           WHERE o.kind = 'HQ' OR x.code = o.code OR x.parent_code = o.code)       AS contract_outlays,
         (SELECT COUNT(*) FROM assets a JOIN organizations x ON x.code = a.org_code
           WHERE o.kind = 'HQ' OR x.code = o.code OR x.parent_code = o.code)       AS asset_count,
         (SELECT COUNT(*) FROM nav_notices n JOIN organizations x ON x.code = n.org_code
           WHERE o.kind = 'HQ' OR x.code = o.code OR x.parent_code = o.code)       AS notice_count
  FROM organizations o
/
CREATE OR REPLACE VIEW v_emt_projects AS
  SELECT p.project_id,
         p.name,
         p.state,
         p.org_code,
         o.name                               AS district,
         o.parent_code                        AS division_code,
         p.division_name                      AS division,
         p.fy2023_allocation,
         p.fy2024_assumed + NVL(p.fy2024_iija, 0) AS fy2024_total,
         p.fy2025_maintenance,
         p.fy2025_operations,
         p.fy2025_total,
         emt_legacy.project_status_label(p.fy2024_assumed + NVL(p.fy2024_iija, 0), p.fy2025_total) AS status,
         p.authorization,
         p.description
  FROM projects p
  LEFT JOIN organizations o ON o.code = p.org_code
/
CREATE OR REPLACE VIEW v_emt_hazard_mix AS
  SELECT NVL(hazard, 'Undetermined') AS hazard, COUNT(*) AS dam_count
  FROM assets
  GROUP BY NVL(hazard, 'Undetermined')
/
CREATE OR REPLACE VIEW v_emt_condition_mix AS
  SELECT NVL(condition, 'Not Rated') AS condition, COUNT(*) AS dam_count
  FROM assets
  GROUP BY NVL(condition, 'Not Rated')
/
CREATE OR REPLACE VIEW v_emt_obligations_by_period AS
  SELECT fiscal_year, period, TO_CHAR(fiscal_year) || ' P' || LPAD(period, 2, '0') AS fy_period, obligated
  FROM agency_obligations_by_period
/
CREATE OR REPLACE VIEW v_emt_lock_status AS
  SELECT observation_id,
         river_name,
         river_code,
         lock_number,
         lock_name,
         lock_mile,
         reading_at,
         upper_gage_ft,
         lower_gage_ft,
         pending_arrivals,
         locking_now,
         locked_up_24h + locked_down_24h AS lockages_24h,
         avg_delay_24h_min,
         CASE WHEN avg_delay_24h_min >= 120 THEN 'Severe delay'
              WHEN avg_delay_24h_min >= 60  THEN 'Delayed'
              WHEN avg_delay_24h_min IS NULL THEN 'No data'
              ELSE 'Normal' END        AS delay_status,
         notes
  FROM lock_observations
/
