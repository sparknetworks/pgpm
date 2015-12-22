/*
    Migration script from version 0.1.12 to 0.1.12 (or higher if tool doesn't find other migration scripts)
 */

CREATE TABLE _pgpm.table_evolutions_log (
    t_evo_id SERIAL NOT NULL,
    t_evo_file_name TEXT,
    t_evo_package INTEGER,
    CONSTRAINT table_evolutions_log_pkey PRIMARY KEY (t_evo_id),
    CONSTRAINT package_fkey FOREIGN KEY (t_evo_package) REFERENCES _pgpm.packages (pkg_id)
);