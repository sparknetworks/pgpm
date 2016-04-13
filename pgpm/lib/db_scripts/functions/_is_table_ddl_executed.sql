CREATE OR REPLACE FUNCTION _is_table_ddl_executed(p_file_name         TEXT,
                                                  p_pkg_name          TEXT,
                                                  p_pkg_subclass_name TEXT,
                                                  p_pkg_v_major       INTEGER,
                                                  p_pkg_v_minor       INTEGER DEFAULT 0,
                                                  p_pkg_v_patch       INTEGER DEFAULT 0,
                                                  p_pkg_v_pre         TEXT DEFAULT NULL)
    RETURNS BOOLEAN AS
$BODY$
---
-- @description
-- Checks whether file with table ddl has already been executed
--
-- @param p_file_name
-- File name used to check whether statements were executed
--
-- @returns
-- True if executed, False otherwise
---
DECLARE
    l_existing_pkg_id INTEGER;

    return_value      BOOLEAN;
BEGIN

    IF p_pkg_subclass_name = 'basic'
    THEN
        SELECT pkg_id
        INTO l_existing_pkg_id
        FROM packages
        WHERE pkg_name = p_pkg_name
              AND pkg_subclass IN (SELECT pkg_sc_id
                                   FROM package_subclasses
                                   WHERE pkg_sc_name = p_pkg_subclass_name);
    ELSE
        SELECT pkg_id
        INTO l_existing_pkg_id
        FROM packages
        WHERE pkg_name = p_pkg_name
              AND pkg_subclass IN (SELECT pkg_sc_id
                                   FROM package_subclasses
                                   WHERE pkg_sc_name = p_pkg_subclass_name)
              AND pkg_v_major = p_pkg_v_major
              AND (pkg_v_minor IS NULL OR pkg_v_minor = p_pkg_v_minor)
              AND (pkg_v_patch IS NULL OR pkg_v_patch = p_pkg_v_patch)
              AND (pkg_v_pre IS NULL OR pkg_v_pre = p_pkg_v_pre)
              AND pkg_old_rev IS NULL;
    END IF;

    IF FOUND
    THEN
        SELECT EXISTS(
            SELECT t_evo_id
            FROM table_evolutions_log
            WHERE t_evo_file_name = p_file_name
                  AND t_evo_package = l_existing_pkg_id
        )
        INTO return_value;

        RETURN return_value;
    ELSE
        RETURN FALSE;
    END IF;

END;
$BODY$
LANGUAGE 'plpgsql' VOLATILE SECURITY DEFINER;
