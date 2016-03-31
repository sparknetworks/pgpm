--
--
--

set SEARCH_PATH to audit,public;

DROP FUNCTION report_audit() ;

CREATE OR REPLACE FUNCTION report_audit() RETURNS text AS $body$
DECLARE
BEGIN
  RETURN 'Not yet implemented'::text;
END;
$body$
language 'plpgsql';

COMMENT ON FUNCTION report_audit() IS $body$
Return (filtered) audit-trail.

Arguments:
   TODO:

$body$;
