/*
    Migration script from version 0.1.0 to 0.1.1 (or higher if tool doesn't find other migration scripts)
 */
CREATE TABLE {schema_name}.migrations_log
(
    m_id SERIAL NOT NULL,
    m_low_v TEXT,
    m_high_v TEXT,
    m_created TIMESTAMP DEFAULT NOW(),
    CONSTRAINT migrations_log_pkey PRIMARY KEY (m_id)
);
INSERT INTO {schema_name}.migrations_log (m_low_v, m_high_v)
    VALUES ('0.0.1', '0.0.6');
INSERT INTO {schema_name}.migrations_log (m_low_v, m_high_v)
    VALUES ('0.0.7', '0.1.0');
COMMENT ON TABLE {schema_name}.migrations_log IS
    'Logs each migration of pgpm to newer version. TODO: add statuses';

ALTER TABLE {schema_name}.deployment_events DROP CONSTRAINT IF EXISTS dpl_ev_pkey;
ALTER TABLE {schema_name}.deployment_events ADD CONSTRAINT dpl_ev_pkey PRIMARY KEY (dpl_ev_pkg_id, dpl_ev_time);