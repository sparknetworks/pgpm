DO
$$BEGIN
    -- Schema will have all info regarding packages. Name, version, dependencies, etc.
    CREATE SCHEMA _pgpm;
    -- Version of package. Tries to follow semver as much as possible considering limited allowed characters
    -- for schema name
    CREATE TYPE _pgpm.package_version as
    (
        major smallint,
        minor smallint,
        patch smallint,
        pre character varying(255),
        metadata character varying(255)
    );
    -- class of package. Can refer to function/types schema, DDL schema
    CREATE TABLE _pgpm.package_classes
    (
        pkg_c_id serial NOT NULL,
        pkg_c_name character varying(255),
        pkg_c_created timestamp without time zone DEFAULT now(),
        pkg_c_last_modified timestamp without time zone DEFAULT now(),
        CONSTRAINT package_class_pkey PRIMARY KEY (pkg_c_id)
    );
    INSERT INTO _pgpm.package_classes (pkg_c_name)
        VALUES ('postgres_sql');
    INSERT INTO _pgpm.package_classes (pkg_c_name)
        VALUES ('postgres_ddl');

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
        pkg_version _pgpm.package_version,
        pkg_class integer,
        pkg_subclass integer,
        pkg_created timestamp without time zone DEFAULT now(),
        pkg_last_modified timestamp without time zone DEFAULT statement_timestamp(),
        CONSTRAINT package_pkey PRIMARY KEY (pkg_id),
        CONSTRAINT package_class_fkey FOREIGN KEY (pkg_class) REFERENCES _pgpm.package_classes (pkg_c_id),
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