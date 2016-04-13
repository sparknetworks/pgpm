CREATE OR REPLACE FUNCTION set_search_path(p_schema_name TEXT, p_v_req TEXT)
    RETURNS JSON AS
$BODY$
---
-- @description
-- Sets search path that includes also all depending
--
-- @param p_schema_name
-- Package (schema) name
--
-- @param p_v_req
-- Package version requirement. Version notation supports:
-- - exact version number either in a format 1_2_3 or 01_02_03 (latter format is for formatting purposes)
-- - x notation like 01_02_XX or 01_02_xx or 1_2_X or 1_2_x
-- - comparison operators like >01_02_03 or <2
-- - x for any latest version of package
-- Package name must comply with naming conventions of postgres, exist as schema and be trackable by pgpm in order to satisfy dependency
--
-- @returns
-- JSON with schema names and exact versions or exception if not found
---
DECLARE
    l_search_path         TEXT;
    l_search_path_deps    TEXT;
    l_listen_text         TEXT;

    l_pkg_version_wrapped RECORD;
    l_pkg_version         RECORD;

    return_value          JSON;
BEGIN

    SET search_path TO _pgpm;
    SELECT _find_schema(p_schema_name, p_v_req) AS version
    INTO l_pkg_version_wrapped;
    l_pkg_version := l_pkg_version_wrapped.version;

    l_search_path := l_pkg_version.pkg_name || '_' ||
                     l_pkg_version.pkg_v_major :: TEXT || '_' ||
                     l_pkg_version.pkg_v_minor :: TEXT || '_' ||
                     l_pkg_version.pkg_v_patch :: TEXT;

    SELECT string_agg(pkg_name || '_' || pkg_v_major || '_' || pkg_v_minor || '_' || pkg_v_patch, ', ')
    FROM packages
    WHERE pkg_id IN (
        SELECT pkg_link_dep_id
        FROM package_dependencies
            JOIN packages ON pkg_id = l_pkg_version.pkg_id
        WHERE pkg_link_core_id = pkg_id
    )
    INTO l_search_path_deps;

    l_search_path := l_search_path || ', ' || l_search_path_deps;

    l_listen_text := 'deployment_events' || '$$' || l_pkg_version.pkg_name;
    EXECUTE 'LISTEN ' || l_listen_text;

    RAISE INFO '%', l_search_path;
    PERFORM set_config('search_path', l_search_path || ', public', FALSE);

    return_value := row_to_json(l_pkg_version);
    RETURN return_value;

END;
$BODY$
LANGUAGE 'plpgsql' VOLATILE SECURITY DEFINER;
