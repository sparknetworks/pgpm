CREATE OR REPLACE FUNCTION ignore_table(target_table REGCLASS)
    RETURNS VOID AS $body$
DECLARE
BEGIN
    PERFORM take_snapshot(target_table);
    EXECUTE 'DROP TRIGGER IF EXISTS audit_trigger_row ON ' || quote_ident(target_table :: TEXT);
    EXECUTE 'DROP TRIGGER IF EXISTS audit_trigger_stm ON ' || quote_ident(target_table :: TEXT);
END;
$body$
LANGUAGE 'plpgsql';

COMMENT ON FUNCTION ignore_table(REGCLASS) IS $body$
Remove auditing triggers from a table and take a final snapshot.

Arguments:
   target_table:     Table name, schema qualified if not on search_path
$body$;
