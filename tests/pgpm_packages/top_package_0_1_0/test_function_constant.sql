CREATE OR REPLACE FUNCTION test_function_constant()
    RETURNS INTEGER AS
$BODY$
---
-- @description
-- Test function that returns constant integer number. Used to test rolling version deployments
--
-- @returns
-- Integer constant value
---
DECLARE
    return_value INTEGER = 5;
BEGIN

    RAISE INFO 'Function returns constant value %', return_value;
    RETURN return_value;

END;
$BODY$
    LANGUAGE 'plpgsql' VOLATILE SECURITY DEFINER;
