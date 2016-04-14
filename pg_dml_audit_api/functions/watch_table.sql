CREATE OR REPLACE FUNCTION watch_table(target_table REGCLASS)
    RETURNS VOID AS $body$
DECLARE
    query_text TEXT;

BEGIN
    EXECUTE 'DROP TRIGGER IF EXISTS audit_trigger_row ON ' || quote_ident(target_table :: TEXT);
    EXECUTE 'DROP TRIGGER IF EXISTS audit_trigger_stm ON ' || quote_ident(target_table :: TEXT);

    query_text = 'CREATE TRIGGER audit_trigger_row AFTER INSERT OR UPDATE OR DELETE ON ' ||
                 quote_ident(target_table :: TEXT) ||
                 ' FOR EACH ROW EXECUTE PROCEDURE audit.if_modified_func();';
    RAISE NOTICE '%', query_text;
    EXECUTE query_text;

    query_text = 'CREATE TRIGGER audit_trigger_stm BEFORE TRUNCATE ON ' ||
                 quote_ident(target_table :: TEXT) ||
                 ' FOR EACH STATEMENT EXECUTE PROCEDURE audit.if_modified_func();';
    RAISE NOTICE '%', query_text;
    EXECUTE query_text;

    PERFORM take_snapshot(target_table);

END;
$body$
LANGUAGE 'plpgsql';

COMMENT ON FUNCTION watch_table(REGCLASS) IS $body$
Add auditing triggers to a table and take a initial snapshot.

Arguments:
   target_table:     Table name, schema qualified if not on search_path
$body$;

