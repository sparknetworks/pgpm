/*
    Migration script from version 0.1.18 to 0.1.18 (or higher if tool doesn't find other migration scripts)
 */
COMMENT ON TABLE _pgpm.table_evolutions_log IS
    'Table tracks all table evolution statements (ALTER TABLE + DML) for pgpm packages';
COMMENT ON COLUMN _pgpm.table_evolutions_log.t_evo_file_name IS
    'File name acts as a key to check whether evolution has already been applied or not';