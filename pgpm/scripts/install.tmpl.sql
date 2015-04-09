DO
$$BEGIN
    CREATE SCHEMA {schema_name};
    GRANT USAGE ON SCHEMA {schema_name} TO public;
    COMMENT ON SCHEMA {schema_name} IS
        'Schema containing all information about postgres packages (name, version, dependencies, etc.)
         and utility functions';

    SET search_path TO {schema_name}, public;

    CREATE TABLE package_subclasses
    (
        pkg_sc_id SERIAL NOT NULL,
        pkg_sc_name TEXT,
        CONSTRAINT package_subclass_pkey PRIMARY KEY (pkg_sc_id)
    );
    INSERT INTO package_subclasses (pkg_sc_name)
        VALUES ('versioned');
    INSERT INTO package_subclasses (pkg_sc_name)
        VALUES ('basic');
    COMMENT ON TABLE package_subclasses IS
        'Subclass of package. Can refer either to versioned schema (that adds suffix at the end)
         or non-versioned (basic) one (without suffix at the end)';

    CREATE TABLE packages
    (
        pkg_id SERIAL NOT NULL,
        pkg_name TEXT,
        pkg_description TEXT,
        pkg_v_major INTEGER,
        pkg_v_minor INTEGER,
        pkg_v_patch INTEGER,
        pkg_v_pre TEXT,
        pkg_v_metadata TEXT,
        pkg_old_rev INTEGER,
        pkg_subclass INTEGER,
        pkg_license TEXT,
        CONSTRAINT package_pkey PRIMARY KEY (pkg_id),
        CONSTRAINT package_subclass_fkey FOREIGN KEY (pkg_subclass) REFERENCES package_subclasses (pkg_sc_id)
    );
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

    CREATE TABLE package_dependencies
    (
        pkg_link_core_id INTEGER NOT NULL,
        pkg_link_dep_id INTEGER NOT NULL CHECK (pkg_link_core_id <> pkg_link_dep_id),
        CONSTRAINT package_dependency_pkey PRIMARY KEY (pkg_link_core_id, pkg_link_dep_id),
        CONSTRAINT package_link_core_fkey FOREIGN KEY (pkg_link_core_id) REFERENCES packages (pkg_id),
        CONSTRAINT package_link_dependency_fkey FOREIGN KEY (pkg_link_dep_id) REFERENCES packages (pkg_id)
    );
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