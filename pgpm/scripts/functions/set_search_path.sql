CREATE OR REPLACE FUNCTION set_search_path(p_schema_name TEXT, p_v_req TEXT)
    RETURNS RECORD AS
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
    return_value RECORD;
BEGIN

    SELECT _find_schema(p_schema_name, p_v_req) INTO return_value;

    RETURN return_value;

END;
$BODY$
    LANGUAGE 'plpgsql' VOLATILE SECURITY DEFINER;
