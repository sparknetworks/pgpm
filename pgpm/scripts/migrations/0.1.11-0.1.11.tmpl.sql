/*
    Migration script from version 0.1.11 to 0.1.11 (or higher if tool doesn't find other migration scripts)
 */

ALTER TABLE _pgpm.ddl_changes_log DROP COLUMN dpl_ev_id;
ALTER TABLE _pgpm.deployment_events ADD COLUMN dpl_ev_txid BIGINT;
