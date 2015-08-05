DO
$$BEGIN
    CREATE SCHEMA {schema_name};
    SET search_path TO {schema_name}, public;

    CREATE TABLE package_subclasses
    (
        pkg_sc_id SERIAL NOT NULL,
        pkg_sc_name TEXT,
        pkg_sc_created TIMESTAMP DEFAULT now(),
        pkg_sc_last_modified TIMESTAMP DEFAULT now(),
        CONSTRAINT package_subclass_pkey PRIMARY KEY (pkg_sc_id)
    );
    INSERT INTO package_subclasses (pkg_sc_name)
        VALUES ('versioned');
    INSERT INTO package_subclasses (pkg_sc_name)
        VALUES ('basic');

    -- info on packages
    CREATE TABLE packages
    (
        pkg_id serial NOT NULL,
        pkg_name character varying(255),
        pkg_description text,
        pkg_v_major integer,
        pkg_v_minor integer,
        pkg_v_patch integer,
        pkg_v_pre character varying(255),
        pkg_v_metadata character varying(255),
        pkg_old_rev integer,
        pkg_vcs_ref varchar(255),
        pkg_subclass integer,
        pkg_license text,
        pkg_created timestamp without time zone DEFAULT now(),
        pkg_last_modified timestamp without time zone DEFAULT statement_timestamp(),
        CONSTRAINT package_pkey PRIMARY KEY (pkg_id),
        CONSTRAINT package_subclass_fkey FOREIGN KEY (pkg_subclass) REFERENCES package_subclasses (pkg_sc_id)
    );

    -- info on package dependencies
    CREATE TABLE package_dependencies
    (
        pkg_dep_id serial NOT NULL,
        pkg_link_core_id integer NOT NULL,
        pkg_link_dep_id integer NOT NULL CHECK (pkg_link_core_id <> pkg_link_dep_id),
        CONSTRAINT package_dependency_pkey PRIMARY KEY (pkg_dep_id),
        CONSTRAINT package_link_core_fkey FOREIGN KEY (pkg_link_core_id) REFERENCES packages (pkg_id),
        CONSTRAINT package_link_dependency_fkey FOREIGN KEY (pkg_link_dep_id) REFERENCES packages (pkg_id)
    );

END$$;