CREATE OR REPLACE FUNCTION _is_table_ddl_executed(p_file_name TEXT)
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
    return_value BOOLEAN;
BEGIN

    SELECT EXISTS (SELECT t_evo_id FROM table_evolutions_log WHERE t_evo_file_name=p_file_name) INTO return_value;

    RETURN return_value;

END;
$BODY$
    LANGUAGE 'plpgsql' VOLATILE SECURITY DEFINER;
