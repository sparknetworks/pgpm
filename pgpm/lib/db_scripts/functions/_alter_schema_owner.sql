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
    l_schema    TEXT;
    l_functions TEXT;
    l_tables    TEXT;
    l_sequences TEXT;
    l_views     TEXT;
    l_domains   TEXT;
    l_triggers  TEXT;
    l_types     TEXT;

BEGIN

    l_schema := 'ALTER SCHEMA '
                || quote_ident(p_schema)
                || ' OWNER TO '
                || quote_ident(p_owner)
                || ';';

    SELECT string_agg('ALTER FUNCTION '
                      || quote_ident(n.nspname) || '.'
                      || quote_ident(p.proname) || '('
                      || pg_catalog.pg_get_function_identity_arguments(p.oid)
                      || ') OWNER TO ' || p_owner || ';'
    , E'\n') AS _sql
    FROM pg_catalog.pg_proc p
        JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = p_schema
    INTO l_functions;
    IF l_functions IS NULL
    THEN
        l_functions := '';
    END IF;

    SELECT string_agg(
        'ALTER TABLE ' || quote_ident(schemaname) || '.' || quote_ident(tablename) || ' OWNER TO ' || p_owner || ';',
        E'\n')
    FROM pg_tables
    WHERE schemaname = p_schema
    INTO l_tables;
    IF l_tables IS NULL
    THEN
        l_tables := '';
    END IF;

    SELECT string_agg(
        'ALTER SEQUENCE ' || quote_ident(sequence_schema) || '.' || quote_ident(sequence_name) || ' OWNER TO ' ||
        p_owner || ';', E'\n')
    FROM information_schema.sequences
    WHERE sequence_schema = p_schema
    INTO l_sequences;
    IF l_sequences IS NULL
    THEN
        l_sequences := '';
    END IF;

    SELECT string_agg(
        'ALTER VIEW ' || quote_ident(table_schema) || '.' || quote_ident(table_name) || ' OWNER TO ' || p_owner || ';',
        E'\n')
    FROM information_schema.views
    WHERE table_schema = p_schema
    INTO l_views;
    IF l_views IS NULL
    THEN
        l_views := '';
    END IF;

    SELECT string_agg(
        'ALTER DOMAIN ' || quote_ident(domain_schema) || '.' || quote_ident(domain_name) || ' OWNER TO ' || p_owner ||
        ';', E'\n')
    FROM information_schema.domains
    WHERE domain_schema = p_schema
    INTO l_domains;
    IF l_domains IS NULL
    THEN
        l_domains := '';
    END IF;

    SELECT string_agg(
        'ALTER TRIGGER ' || quote_ident(trigger_schema) || '.' || quote_ident(trigger_name) || ' OWNER TO ' || p_owner
        || ';', E'\n')
    FROM information_schema.triggers
    WHERE trigger_schema = p_schema
    INTO l_triggers;
    IF l_triggers IS NULL
    THEN
        l_triggers := '';
    END IF;

    SELECT string_agg(
        'ALTER TYPE ' || quote_ident(user_defined_type_schema) || '.' || quote_ident(user_defined_type_name) ||
        ' OWNER TO ' || p_owner || ';', E'\n')
    FROM information_schema.user_defined_types
    WHERE user_defined_type_schema = p_schema
    INTO l_types;
    IF l_types IS NULL
    THEN
        l_types := '';
    END IF;

    EXECUTE l_schema || l_functions || l_tables || l_sequences || l_views || l_domains || l_triggers || l_types;

END;
$BODY$
LANGUAGE 'plpgsql' VOLATILE SECURITY INVOKER;