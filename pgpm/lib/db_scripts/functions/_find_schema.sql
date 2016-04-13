CREATE OR REPLACE FUNCTION _find_schema(p_schema_name TEXT, p_v_req TEXT)
    RETURNS RECORD AS
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
-- Record containing schema name and exact version or exception if not found in the following format:
-- pkg_name TEXT, pkg_v_major INTEGER, pkg_v_minor INTEGER, pkg_v_patch INTEGER
---
DECLARE
    c_re_version TEXT = '^(<=|>=|<|>{0,2})(\d*|x*)_?(\d*|x*)_?(\d*|x*)';
    l_v_matches  TEXT [];

    l_v_major    INTEGER;
    l_v_minor    INTEGER;
    l_v_patch    INTEGER;

    return_value RECORD;
BEGIN

    SELECT regexp_matches(p_v_req, c_re_version, 'gi')
    INTO l_v_matches;

    IF l_v_matches [2] ~* '^x+|^$'
    THEN
        SELECT max(pkg_v_major)
        FROM packages
        WHERE pkg_name = p_schema_name
        INTO l_v_major;
    ELSE
        l_v_major := l_v_matches [2] :: INTEGER;
    END IF;

    IF l_v_matches [3] ~* '^x+|^$'
    THEN
        SELECT max(pkg_v_minor)
        FROM packages
        WHERE pkg_name = p_schema_name
              AND pkg_v_major = l_v_major
        INTO l_v_minor;
    ELSE
        l_v_minor := l_v_matches [3] :: INTEGER;
    END IF;

    IF l_v_matches [4] ~* '^x+|^$'
    THEN
        SELECT max(pkg_v_patch)
        FROM packages
        WHERE pkg_name = p_schema_name
              AND pkg_v_major = l_v_major
              AND pkg_v_minor = l_v_minor
        INTO l_v_patch;
    ELSE
        l_v_patch := l_v_matches [4] :: INTEGER;
    END IF;

    CASE l_v_matches [1]
        WHEN '=', ''
        THEN
            SELECT DISTINCT
                pkg_id,
                pkg_name,
                pkg_v_major,
                pkg_v_minor,
                pkg_v_patch
            FROM packages
            WHERE pkg_name = p_schema_name
                  AND pkg_v_major = l_v_major
                  AND pkg_v_minor = l_v_minor
                  AND pkg_v_patch = l_v_patch
            INTO return_value;
        WHEN '<'
        THEN
            SELECT DISTINCT
                pkg_id,
                pkg_name,
                pkg_v_major,
                pkg_v_minor,
                pkg_v_patch
            FROM packages
            WHERE pkg_name = p_schema_name
                  AND (pkg_v_major < l_v_major
                       OR (pkg_v_major = l_v_major
                           AND pkg_v_minor < l_v_minor)
                       OR (pkg_v_major = l_v_major
                           AND pkg_v_minor = l_v_minor
                           AND pkg_v_patch < l_v_patch))
            INTO return_value;
        WHEN '>'
        THEN
            SELECT DISTINCT
                pkg_id,
                pkg_name,
                pkg_v_major,
                pkg_v_minor,
                pkg_v_patch
            FROM packages
            WHERE pkg_name = p_schema_name
                  AND (pkg_v_major > l_v_major
                       OR (pkg_v_major = l_v_major
                           AND pkg_v_minor > l_v_minor)
                       OR (pkg_v_major = l_v_major
                           AND pkg_v_minor = l_v_minor
                           AND pkg_v_patch > l_v_patch))
            INTO return_value;
        WHEN '<='
        THEN
            SELECT DISTINCT
                pkg_id,
                pkg_name,
                pkg_v_major,
                pkg_v_minor,
                pkg_v_patch
            FROM packages
            WHERE pkg_name = p_schema_name
                  AND (pkg_v_major <= l_v_major
                       OR (pkg_v_major = l_v_major
                           AND pkg_v_minor <= l_v_minor)
                       OR (pkg_v_major = l_v_major
                           AND pkg_v_minor = l_v_minor
                           AND pkg_v_patch <= l_v_patch))
            INTO return_value;
        WHEN '>='
        THEN
            SELECT DISTINCT
                pkg_id,
                pkg_name,
                pkg_v_major,
                pkg_v_minor,
                pkg_v_patch
            FROM packages
            WHERE pkg_name = p_schema_name
                  AND (pkg_v_major >= l_v_major
                       OR (pkg_v_major = l_v_major
                           AND pkg_v_minor >= l_v_minor)
                       OR (pkg_v_major = l_v_major
                           AND pkg_v_minor = l_v_minor
                           AND pkg_v_patch >= l_v_patch))
            INTO return_value;
    ELSE
        RAISE EXCEPTION 'Invalid logical operand. Only <, >, =, <=, >=, = or no operand are allowed.'
        USING ERRCODE = '20000';
    END CASE;

    RETURN return_value;

END;
$BODY$
LANGUAGE 'plpgsql' VOLATILE SECURITY DEFINER;
