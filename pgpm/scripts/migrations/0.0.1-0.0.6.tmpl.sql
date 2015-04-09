/*
    Migration script from version 0.0.1 to 0.0.6 (or higher if tool doesn't find other migration scripts)
 */
DO
$$BEGIN
    SET search_path TO {schema_name}, public;
    GRANT USAGE ON SCHEMA {schema_name} TO public;
    COMMENT ON SCHEMA {schema_name} IS
        'Schema containing all information about postgres packages (name, version, dependencies, etc.)
         and utility functions';

    -- drop created and last modified in subclasses, add comment and change varchar to text
    ALTER TABLE package_subclasses DROP COLUMN pkg_sc_created;
    ALTER TABLE package_subclasses DROP COLUMN pkg_sc_last_modified;
    ALTER TABLE package_subclasses ALTER COLUMN pkg_sc_name TYPE TEXT;
    COMMENT ON TABLE package_subclasses IS
        'Subclass of package. Can refer either to versioned schema (that adds suffix at the end)
         or non-versioned (basic) one (without suffix at the end)';

    -- remove vcf reference, created and last modified (will be moved to deployment_events table), add comments,
    -- change varchar to text and bump version of pgpm to 0.0.6
    ALTER TABLE packages DROP COLUMN pkg_created;
    ALTER TABLE packages DROP COLUMN pkg_last_modified;
    ALTER TABLE packages DROP COLUMN pkg_vcs_ref;
    ALTER TABLE packages ALTER COLUMN pkg_name TYPE TEXT;
    ALTER TABLE packages ALTER COLUMN pkg_v_pre TYPE TEXT;
    ALTER TABLE packages ALTER COLUMN pkg_v_metadata TYPE TEXT;
    UPDATE packages SET pkg_v_major = 0, pkg_v_minor = 0, pkg_v_patch = 6 WHERE pkg_name = '{schema_name}';
    COMMENT ON TABLE packages IS
        'Information about package (schema) tracked with pgpm.';
    COMMENT ON COLUMN packages.pkg_v_major IS
        'Major part of version of a package as seen in semver';
    COMMENT ON COLUMN packages.pkg_v_minor IS
        'Minor part of version of a package as seen in semver';
    COMMENT ON COLUMN packages.pkg_v_patch IS
        'Patch part of version of a package as seen in semver';
    COMMENT ON COLUMN packages.pkg_v_pre IS
        'Pre part of version of a package as seen in semver';
    COMMENT ON COLUMN packages.pkg_v_metadata IS
        'Metadata part of version of a package as seen in semver';
    COMMENT ON COLUMN packages.pkg_old_rev IS
        'Incremental number of the revision of the package of the same version.
         Used the following way. If package deployed with the version of already existing package in moderate mode then
         old package is renamed by adding an ending with incremental revision (starting with 0)';
    COMMENT ON COLUMN packages.pkg_license IS
        'Name of license (or a link) of a package';

    -- change Primary key to combination of 2 keys and remove old key
    ALTER TABLE package_dependencies DROP CONSTRAINT package_dependency_pkey;
    ALTER TABLE package_dependencies ADD CONSTRAINT package_dependency_pkey PRIMARY KEY (pkg_link_core_id, pkg_link_dep_id);
    COMMENT ON TABLE package_dependencies IS
        'Many to many relationship between dependant packages. Package cannot depend on itself';

    CREATE TABLE deployment_events
    (
        dpl_ev_pkg_id INTEGER,
        dpl_ev_vcs_ref TEXT,
        dpl_ev_vcs_link TEXT,
        dpl_ev_time TIMESTAMP DEFAULT NOW(),
        dpl_ev_issue_id TEXT,
        dpl_ev_issue_link TEXT,
        CONSTRAINT dpl_ev_pkg_fkey FOREIGN KEY (dpl_ev_pkg_id) REFERENCES packages (pkg_id)
    );
    COMMENT ON TABLE deployment_events IS
        'Table tracks all deployments tracked by pgpm';
    COMMENT ON COLUMN deployment_events.dpl_ev_vcs_ref IS
        'Reference to VCS point that was installed.
         In case of git, best option is to put here a specific commit reference.
         In case of SVN, revision number.';
    COMMENT ON COLUMN deployment_events.dpl_ev_vcs_link IS
        'Link to VCS repository.';
    COMMENT ON COLUMN deployment_events.dpl_ev_time IS
        'Deployment time';
    COMMENT ON COLUMN deployment_events.dpl_ev_issue_id IS
        'ID of an issue in issue tracker. E.g. ABS-111 for JIRA.';
    COMMENT ON COLUMN deployment_events.dpl_ev_issue_link IS
        'Link to an issue related to this deployment in issue tracker.';

END$$;