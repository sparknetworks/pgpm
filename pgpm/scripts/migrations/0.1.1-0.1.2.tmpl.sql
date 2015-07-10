/*
    Migration script from version 0.1.0 to 0.1.1 (or higher if tool doesn't find other migration scripts)
 */
ALTER TABLE {schema_name}.deployment_events ADD PRIMARY KEY (dpl_ev_pkg_id, dpl_ev_time);