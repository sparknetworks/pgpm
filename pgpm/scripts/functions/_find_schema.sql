CREATE OR REPLACE FUNCTION _find_schema(p_schema_name TEXT, p_v_req TEXT)
    RETURNS JSON AS
$BODY$
---
-- @description
-- Searches for existing schema (package) within registered packages in _pgpm schema
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
-- JSON string containing schema name and exact version or exception if not found
---
DECLARE
    c_re_version TEXT = '^(<=|>=|<|>{0,2})(\d*|x*)_?(\d*|x*)_?(\d*|x*)';
    l_v_matches TEXT[];
BEGIN

    SELECT regexp_matches(p_v_req, c_re_version, 'g') INTO l_v_matches;

--     IF l_v_matches[0] = '='
--     SELECT pkg_name FROM _pgpm.packages WHERE pkg_name = '_pgpm';
-- TODO: Implement
END;
$BODY$
    LANGUAGE 'plpgsql' VOLATILE SECURITY DEFINER
