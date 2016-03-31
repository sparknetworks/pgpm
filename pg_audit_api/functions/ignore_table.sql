---
---
---

CREATE OR REPLACE FUNCTION ignore_table(target_table regclass) RETURNS void AS $body$
DECLARE
BEGIN
    -- TODO: take final snapshot
    EXECUTE 'DROP TRIGGER IF EXISTS audit_trigger_row ON ' || quote_ident(target_table::TEXT);
    EXECUTE 'DROP TRIGGER IF EXISTS audit_trigger_stm ON ' || quote_ident(target_table::TEXT);
END;
$body$
language 'plpgsql';

COMMENT ON FUNCTION audit.audit_table(regclass) IS $body$
Remove auditing from a table.

Arguments:
   target_table:     Table name, schema qualified if not on search_path
$body$;
