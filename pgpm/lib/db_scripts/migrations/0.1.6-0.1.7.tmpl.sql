/*
    Migration script from version 0.1.6 to 0.1.7 (or higher if tool doesn't find other migration scripts)
 */
ALTER TABLE {schema_name}.packages DROP CONSTRAINT IF EXISTS pkg_unique;
ALTER TABLE {schema_name}.packages ADD CONSTRAINT pkg_unique UNIQUE (pkg_name, pkg_v_major, pkg_v_minor, pkg_v_patch, pkg_v_pre, pkg_old_rev);