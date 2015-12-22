/*
    Migration script from version 0.1.13 to 0.1.17 (or higher if tool doesn't find other migration scripts)
 */

ALTER TABLE _pgpm.table_evolutions_log ADD COLUMN t_evo_created TIMESTAMP DEFAULT NOW();
