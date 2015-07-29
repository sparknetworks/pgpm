/*
    Migration script from version 0.1.8 to 0.1.9 (or higher if tool doesn't find other migration scripts)
 */
CREATE TABLE {schema_name}.package_statuses
(
    pkg_s_id SERIAL NOT NULL,
    pkg_s_name TEXT,
    CONSTRAINT pkg_s_pkey PRIMARY KEY (pkg_s_id)
);
COMMENT ON TABLE {schema_name}.package_statuses IS
    'Package statuses';
INSERT INTO {schema_name}.package_statuses (pkg_s_id, pkg_s_name)
    VALUES (1, 'ADDED');
INSERT INTO {schema_name}.package_statuses (pkg_s_id, pkg_s_name)
    VALUES (2, 'IN PROGRESS');
INSERT INTO {schema_name}.package_statuses (pkg_s_id, pkg_s_name)
    VALUES (3, 'DELETED');

ALTER TABLE {schema_name}.packages ADD COLUMN pkg_status INTEGER DEFAULT 1;
ALTER TABLE {schema_name}.packages ADD CONSTRAINT pkg_status_fkey FOREIGN KEY (pkg_status) REFERENCES {schema_name}.package_statuses (pkg_s_id);