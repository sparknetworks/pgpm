CREATE OR REPLACE FUNCTION set_search_path(p_schema_name TEXT, p_v_req TEXT)
    RETURNS json AS
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
-- Records containing schema names and exact versions or exception if not found
---
DECLARE
    l_search_path TEXT;
    l_pkg_version_wrapped RECORD;
    l_pkg_version RECORD;
    l_linked_packages SETOF RECORD;
    l_linked_packages_array TEXT ARRAY;

    return_value json;
BEGIN

    SET search_path TO _pgpm;
    SELECT _find_schema(p_schema_name, p_v_req) AS version INTO l_pkg_version_wrapped;
    l_pkg_version := l_pkg_version_wrapped.version;

    SELECT pkg_id, pkg_name, pkg_v_major, pkg_v_minor, pkg_v_patch
        WHERE pkg_id = pkg_link_core_id

    l_search_path := l_pkg_version.pkg_name || '_' || l_pkg_version.pkg_v_major::text || '_' || l_pkg_version.pkg_v_minor::text || '_' || l_pkg_version.pkg_v_patch::text;
    SET search_path TO l_search_path, public;

    return_value := row_to_json(l_pkg_version);
    RETURN return_value;

END;
$BODY$
    LANGUAGE 'plpgsql' VOLATILE SECURITY DEFINER;
