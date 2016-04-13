CREATE OR REPLACE FUNCTION _log_ddl_change()
    RETURNS EVENT_TRIGGER AS
$BODY$
---
-- @description
-- Logs any DDL changes to the DB
--
---
DECLARE
    l_current_query TEXT;
    l_txid BIGINT;
BEGIN

    SELECT current_query() INTO l_current_query;
    SELECT txid_current() INTO l_txid;
    INSERT INTO _pgpm.ddl_changes_log (ddl_change)
    SELECT l_current_query
    WHERE
        NOT EXISTS (
            SELECT ddl_change_txid, ddl_change FROM _pgpm.ddl_changes_log
            WHERE ddl_change_txid = l_txid AND ddl_change = l_current_query
        );

    -- Notify external channels of ddl change
    PERFORM pg_notify('ddl_change', "session_user"());

END;
$BODY$
LANGUAGE 'plpgsql' VOLATILE SECURITY DEFINER;