CREATE OR REPLACE FUNCTION _log_table_evolution(p_t_evo_file_name TEXT, p_t_evo_package INTEGER)
    RETURNS VOID AS
$BODY$
---
-- @description
-- Adds information about executed table evolution script to log table
--
-- @param p_t_evo_file_name
-- File name with executed statements.
--
-- @param p_t_evo_package
-- Related package id
--
-- @param p_pkg_old_rev
-- higher border of version that is applicaple for this migration
--
---
BEGIN

    INSERT INTO table_evolutions_log (t_evo_file_name, t_evo_package)
    VALUES (p_t_evo_file_name, p_t_evo_package);
END;
$BODY$
LANGUAGE 'plpgsql' VOLATILE SECURITY DEFINER;