/*
    Migration script from version 0.1.19 to 0.1.33 (or higher if tool doesn't find other migration scripts)
 */

ALTER TABLE _pgpm.ddl_changes_log ALTER COLUMN ddl_change_user SET DEFAULT session_user;