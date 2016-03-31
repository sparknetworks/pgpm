---
---
---

CREATE OR REPLACE FUNCTION watch_table(target_table regclass) RETURNS void AS $body$
DECLARE
  query_text text;
BEGIN
    EXECUTE 'DROP TRIGGER IF EXISTS audit_trigger_row ON ' || quote_ident(target_table::TEXT);
    EXECUTE 'DROP TRIGGER IF EXISTS audit_trigger_stm ON ' || quote_ident(target_table::TEXT);

    query_text = 'CREATE TRIGGER audit_trigger_row AFTER INSERT OR UPDATE OR DELETE ON ' ||
                 quote_ident(target_table::TEXT) ||
                 ' FOR EACH ROW EXECUTE PROCEDURE audit.if_modified_func();';
        RAISE NOTICE '%', query_text;
        EXECUTE query_text;

    query_text = 'CREATE TRIGGER audit_trigger_stm BEFORE TRUNCATE ON ' ||
                 quote_ident(target_table::TEXT) ||
                 ' FOR EACH STATEMENT EXECUTE PROCEDURE audit.if_modified_func();';
        RAISE NOTICE '%', query_text;
        EXECUTE query_text;
    -- TODO: take initial snapshot
END;
$body$
language 'plpgsql';

COMMENT ON FUNCTION watch_table(regclass) IS $body$
Add auditing support to a table.

Arguments:
   target_table:     Table name, schema qualified if not on search_path
$body$;

