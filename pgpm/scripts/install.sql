DO
$$BEGIN
    -- Schema will have all info regarding packages. Name, version, dependencies, etc.
    CREATE SCHEMA _pgpm;

    -- subclass of package. Can refer either versioned schema (that adds suffix at the end) or non-versioned
    CREATE TABLE _pgpm.package_subclasses
    (
        pkg_sc_id serial NOT NULL,
        pkg_sc_name character varying(255),
        pkg_sc_created timestamp without time zone DEFAULT now(),
        pkg_sc_last_modified timestamp without time zone DEFAULT now(),
        CONSTRAINT package_subclass_pkey PRIMARY KEY (pkg_sc_id)
    );
    INSERT INTO _pgpm.package_subclasses (pkg_sc_name)
        VALUES ('versioned');
    INSERT INTO _pgpm.package_subclasses (pkg_sc_name)
        VALUES ('basic');

    -- info on packages
    CREATE TABLE _pgpm.packages
    (
        pkg_id serial NOT NULL,
        pkg_name character varying(255),
        pkg_description text,
        pkg_v_major smallint,
        pkg_v_minor smallint,
        pkg_v_patch smallint,
        pkg_v_pre character varying(255),
        pkg_v_metadata character varying(255),
        pkg_subclass integer,
        pkg_created timestamp without time zone DEFAULT now(),
        pkg_last_modified timestamp without time zone DEFAULT statement_timestamp(),
        CONSTRAINT package_pkey PRIMARY KEY (pkg_id),
        CONSTRAINT package_subclass_fkey FOREIGN KEY (pkg_subclass) REFERENCES _pgpm.package_subclasses (pkg_sc_id)
    );

    -- info on package dependencies
    CREATE TABLE _pgpm.package_dependencies
    (
        pkg_dep_id serial NOT NULL,
        pkg_link_core_id integer NOT NULL,
        pkg_link_dep_id integer NOT NULL CHECK (pkg_link_core_id <> pkg_link_dep_id),
        CONSTRAINT package_dependency_pkey PRIMARY KEY (pkg_dep_id),
        CONSTRAINT package_link_core_fkey FOREIGN KEY (pkg_link_core_id) REFERENCES _pgpm.packages (pkg_id),
        CONSTRAINT package_link_dependency_fkey FOREIGN KEY (pkg_link_dep_id) REFERENCES _pgpm.packages (pkg_id)
    );

END$$;