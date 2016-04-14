CREATE OR REPLACE FUNCTION report_audit()
    RETURNS TEXT AS $body$
DECLARE
BEGIN
    RETURN 'Not yet implemented' :: TEXT;
END;
$body$
LANGUAGE 'plpgsql';

COMMENT ON FUNCTION report_audit() IS $body$
Return (filtered) audit-trail.

Arguments:
   TODO:

$body$;
