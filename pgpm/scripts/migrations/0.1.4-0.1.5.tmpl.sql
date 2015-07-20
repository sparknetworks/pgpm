/*
    Migration script from version 0.1.4 to 0.1.5 (or higher if tool doesn't find other migration scripts)
 */
ALTER TABLE {schema_name}.deployment_events DROP CONSTRAINT IF EXISTS dpl_ev_pkey;
ALTER TABLE {schema_name}.deployment_events ADD COLUMN dpl_ev_id SERIAL NOT NULL;
ALTER TABLE {schema_name}.deployment_events ADD CONSTRAINT dpl_ev_pkey PRIMARY KEY (dpl_ev_id);