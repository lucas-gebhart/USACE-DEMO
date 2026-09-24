-- The "before" tier: business logic the way an APEX application typically holds
-- it, in a PL/SQL package called from page processes and report regions. The
-- FastAPI service can call this package unchanged (see /v1/legacy/*), which is
-- what lets the migration proceed page by page against one database.

CREATE OR REPLACE PACKAGE emt_legacy AS
  FUNCTION district_dashboard (p_org_code IN VARCHAR2) RETURN SYS_REFCURSOR;
  FUNCTION project_status_label (p_fy2024 IN NUMBER, p_fy2025 IN NUMBER) RETURN VARCHAR2;
END emt_legacy;
/
CREATE OR REPLACE PACKAGE BODY emt_legacy AS

  FUNCTION project_status_label (p_fy2024 IN NUMBER, p_fy2025 IN NUMBER) RETURN VARCHAR2 IS
  BEGIN
    IF p_fy2025 IS NULL OR p_fy2024 IS NULL OR p_fy2024 = 0 THEN
      RETURN 'UNKNOWN';
    ELSIF p_fy2025 >= p_fy2024 * 1.10 THEN
      RETURN 'GROWING';
    ELSIF p_fy2025 <= p_fy2024 * 0.90 THEN
      RETURN 'SHRINKING';
    END IF;
    RETURN 'STEADY';
  END project_status_label;

  FUNCTION district_dashboard (p_org_code IN VARCHAR2) RETURN SYS_REFCURSOR IS
    l_cur SYS_REFCURSOR;
  BEGIN
    OPEN l_cur FOR
      SELECT p.project_id,
             p.name,
             p.state,
             p.fy2024_assumed,
             p.fy2025_total,
             emt_legacy.project_status_label(p.fy2024_assumed, p.fy2025_total) AS status_label,
             (SELECT LISTAGG(b.business_line || ':' || b.amount, ',')
                     WITHIN GROUP (ORDER BY b.amount DESC)
                FROM project_business_lines b
               WHERE b.project_id = p.project_id) AS business_lines
        FROM projects p
       WHERE p.org_code = p_org_code
       ORDER BY p.fy2025_total DESC NULLS LAST;
    RETURN l_cur;
  END district_dashboard;

END emt_legacy;
/
