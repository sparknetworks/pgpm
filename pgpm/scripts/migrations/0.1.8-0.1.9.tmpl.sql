/*
    Migration script from version 0.1.8 to 0.1.9 (or higher if tool doesn't find other migration scripts)
 */
CREATE TABLE IF NOT EXISTS {schema_name}.package_statuses
(
    pkg_s_id SERIAL NOT NULL,
    pkg_s_name TEXT,
    CONSTRAINT pkg_s_pkey PRIMARY KEY (pkg_s_id)
);
COMMENT ON TABLE {schema_name}.package_statuses IS
    'Package statuses';
INSERT INTO {schema_name}.package_statuses (pkg_s_id, pkg_s_name)
SELECT 1, 'ADDED'
WHERE
    NOT EXISTS (
        SELECT pkg_s_id, pkg_s_name FROM {schema_name}.package_statuses
        WHERE pkg_s_id = 1
    );

INSERT INTO {schema_name}.package_statuses (pkg_s_id, pkg_s_name)
SELECT 2, 'IN PROGRESS'
WHERE
    NOT EXISTS (
        SELECT pkg_s_id, pkg_s_name FROM {schema_name}.package_statuses
        WHERE pkg_s_id = 2
    );

INSERT INTO {schema_name}.package_statuses (pkg_s_id, pkg_s_name)
SELECT 3, 'DELETED'
WHERE
    NOT EXISTS (
        SELECT pkg_s_id, pkg_s_name FROM {schema_name}.package_statuses
        WHERE pkg_s_id = 3
    );

ALTER TABLE {schema_name}.packages ADD COLUMN pkg_status INTEGER DEFAULT 1;
ALTER TABLE {schema_name}.packages ADD CONSTRAINT pkg_status_fkey FOREIGN KEY (pkg_status) REFERENCES {schema_name}.package_statuses (pkg_s_id);