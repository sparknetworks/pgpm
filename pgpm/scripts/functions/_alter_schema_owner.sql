CREATE OR REPLACE FUNCTION _alter_schema_owner(p_schema TEXT, p_owner TEXT)
    RETURNS VOID AS
$BODY$
---
-- @description
-- Alters ownership of schema and all its objects to a specified user.
--
-- @param p_schema
-- Schema name
--
-- @param p_owner
-- New owner user name
--
---
DECLARE
    l_statement TEXT[];

BEGIN
    SELECT string_agg('ALTER FUNCTION '
                || quote_ident(n.nspname) || '.'
                || quote_ident(p.proname) || '('
                || pg_catalog.pg_get_function_identity_arguments(p.oid)
                || ') OWNER TO ' || p_owner || ';'
              , E'\n') AS _sql
    FROM   pg_catalog.pg_proc p
    JOIN   pg_catalog.pg_namespace n ON n.oid = p.pronamespace
    WHERE  n.nspname = p_schema
    INTO l_statement[0];

    SELECT string_agg('ALTER TABLE '|| quote_ident(tablename) ||' OWNER TO ' || p_owner || ';', E'\n')
    FROM pg_tables WHERE schemaname = p_schema
    INTO l_statement[1];

    SELECT string_agg('ALTER SEQUENCE '|| quote_ident(sequence_name) ||' OWNER TO ' || p_owner || ';', E'\n')
    FROM information_schema.sequences WHERE sequence_schema = p_schema
    INTO l_statement[2];

    SELECT string_agg('ALTER VIEW '|| quote_ident(table_name) ||' OWNER TO ' || p_owner || ';', E'\n')
    FROM information_schema.views WHERE table_schema = p_schema
    INTO l_statement[3];

    SELECT string_agg('ALTER DOMAIN '|| quote_ident(domain_name) ||' OWNER TO ' || p_owner || ';', E'\n')
    FROM information_schema.domains WHERE domain_schema = p_schema
    INTO l_statement[4];

    SELECT string_agg('ALTER TRIGGER '|| quote_ident(trigger_name) ||' OWNER TO ' || p_owner || ';', E'\n')
    FROM information_schema.triggers WHERE trigger_schema = p_schema
    INTO l_statement[5];

END;
$BODY$
LANGUAGE 'plpgsql' VOLATILE SECURITY DEFINER;