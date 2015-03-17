/*
    Migration script from version 0.0.1 to 0.0.6 (or higher if tool doesn't find other migration scripts)
 */
DO
$$BEGIN
    SET search_path TO {schema_name}, public;

    -- drop created and last modified in subclasses
    ALTER TABLE package_subclasses DROP COLUMN pkg_sc_created;
    ALTER TABLE package_subclasses DROP COLUMN pkg_sc_last_modified;

    -- remove vcf reference, created and last modified (will be moved to deployment_events table)
    ALTER TABLE packages DROP COLUMN pkg_created;
    ALTER TABLE packages DROP COLUMN pkg_last_modified;
    ALTER TABLE packages DROP COLUMN pkg_vcs_ref;

    -- change Primary key to combination of 2 keys and remove old key
    ALTER TABLE package_dependencies DROP CONSTRAINT package_dependency_pkey;
    ALTER TABLE package_dependencies ADD CONSTRAINT package_dependency_pkey PRIMARY KEY (pkg_link_core_id, pkg_link_dep_id);

    CREATE TABLE deployment_events
    (
        dpl_ev_vcf_ref text
        -- TODO: finish table definition, change text types of existing tables to text, add indexes
    );

END$$;