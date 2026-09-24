-- Representative APEX "page process" (Processing > Processes > PL/SQL Code) for a
-- district dashboard page. This is the shape of logic EMT-style APEX apps carry
-- inside page definitions: bind items (:P20_*), session state, and inline SQL,
-- with no unit test, no code review diff, and no reuse outside this page.
--
-- The equivalent FastAPI route is api/app/routers/orgs.py::district_dashboard,
-- covered by api/tests/test_orgs.py. Both read the same Oracle tables.

DECLARE
  l_total   NUMBER := 0;
  l_count   NUMBER := 0;
BEGIN
  IF :P20_ORG_CODE IS NULL THEN
    apex_error.add_error(
      p_message          => 'Select a district first.',
      p_display_location => apex_error.c_inline_in_notification);
    RETURN;
  END IF;

  SELECT COUNT(*), NVL(SUM(fy2025_total), 0)
    INTO l_count, l_total
    FROM projects
   WHERE org_code = :P20_ORG_CODE;

  :P20_PROJECT_COUNT := l_count;
  :P20_FY25_BUDGET   := TO_CHAR(l_total, 'FML999G999G999G999');

  -- Hazard mix for the "Assets" region, stored as a delimited string in session state
  SELECT LISTAGG(hazard || '=' || cnt, ';') WITHIN GROUP (ORDER BY hazard)
    INTO :P20_HAZARD_MIX
    FROM (SELECT NVL(hazard, 'Undetermined') AS hazard, COUNT(*) AS cnt
            FROM assets
           WHERE org_code = :P20_ORG_CODE
           GROUP BY NVL(hazard, 'Undetermined'));

  apex_util.set_session_state('P20_LAST_REFRESH', TO_CHAR(SYSTIMESTAMP, 'YYYY-MM-DD HH24:MI'));
END;
