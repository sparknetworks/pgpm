CREATE OR REPLACE FUNCTION drop_schema_smart(p_schema_name TEXT, p_dry_run BOOLEAN DEFAULT TRUE,
                                             p_strict      BOOLEAN DEFAULT FALSE)
    RETURNS VOID AS
$BODY$
-----------------------------------------------------------------------------------------------------------------------
--
-- @description
-- To perform command Drop schema cascade for versioned and long unused ( outdated ) schemas
--
-- @return
-- message as output/exception
--
-- @param p_schema_name
-- schema to drop
--
-- @param p_dry_run
-- perform dry run or not
--	p_dry_run=true --> run function in Dry mode
--	p_dry_run=false --> run function in drop mode
--
-- @param p_strict
-- throw the error message when dropping the schema that doesn't not exist or only return the warning ( default )
--
-- --------------------------------------------------------------------------------------------------------------------

DECLARE

    c_user_oid        INTEGER := 16384;
    l_schema_with_dot TEXT;
    _detail           TEXT;
    _hint             TEXT;
    _message          TEXT;

BEGIN

    l_schema_with_dot := p_schema_name || '.';

    -- check schema existance
    RAISE NOTICE 'Checking schema existance...';
    IF NOT EXISTS(SELECT 1
                  FROM information_schema.schemata
                  WHERE schema_name = p_schema_name)
    THEN
        IF p_strict IS TRUE
        THEN
            RAISE EXCEPTION E'Schema % does not exist', p_schema_name;
        ELSE
            RAISE WARNING 'Schema % does not exist', p_schema_name;
            RETURN;
        END IF;
    END IF;

    -- check table existance
    RAISE NOTICE 'Checking if schema contains any tables...';
    IF EXISTS(SELECT 1
              FROM information_schema.tables
              WHERE table_schema = p_schema_name)
    THEN
        RAISE EXCEPTION E'Schema contains at least one table!\n';
    END IF;

    -- checking schema usage in stat_ACTIVITY
    RAISE NOTICE 'Checking whether schema currently in use ...';
    IF EXISTS(SELECT 1
              FROM pg_stat_activity
              WHERE query LIKE '%' || l_schema_with_dot || '%')
    THEN
        RAISE EXCEPTION E'Schema % currently in use\n', p_schema_name;
    END IF;

    -- checking type dependencies
    RAISE NOTICE 'Checking type dependencies...';
    IF EXISTS(SELECT 1
              FROM (
                       SELECT
                           classid :: REGCLASS :: TEXT    AS dep_obj_type,
                           CASE classid
                           WHEN 'pg_class' :: REGCLASS
                               THEN objid :: REGCLASS :: TEXT
                           WHEN 'pg_type' :: REGCLASS
                               THEN objid :: REGTYPE :: TEXT
                           WHEN 'pg_proc' :: REGCLASS
                               THEN objid :: REGPROCEDURE :: TEXT
                           ELSE objid :: TEXT
                           END                            AS dep_obj,
                           objsubid,
                           refclassid :: REGCLASS :: TEXT AS ref_obj_type,
                           CASE refclassid
                           WHEN 'pg_class' :: REGCLASS
                               THEN refobjid :: REGCLASS :: TEXT
                           WHEN 'pg_type' :: REGCLASS
                               THEN refobjid :: REGTYPE :: TEXT
                           WHEN 'pg_proc' :: REGCLASS
                               THEN refobjid :: REGPROCEDURE :: TEXT
                           ELSE refobjid :: TEXT
                           END                            AS ref_obj,
                           refobjsubid,
                           CASE deptype
                           WHEN 'p'
                               THEN 'pinned'
                           WHEN 'i'
                               THEN 'internal'
                           WHEN 'a'
                               THEN 'automatic'
                           WHEN 'n'
                               THEN 'normal'
                           END                            AS dependency_type
                       FROM pg_catalog.pg_depend
                       WHERE objid >= c_user_oid OR refobjid >= c_user_oid) tab1
              WHERE ref_obj LIKE l_schema_with_dot || '%' AND dependency_type = 'normal' AND
                    dep_obj NOT LIKE l_schema_with_dot || '%')
    THEN
        RAISE EXCEPTION E'Schema has type dependencies with other schemas, please contact DBA team. \n';
    END IF;


    IF p_dry_run IS TRUE
    THEN
        RAISE NOTICE 'THIS IS THE DRY RUN. TO DROP SCHEMA % PASS FALSE TO DRY RUN PARAMETER', p_schema_name;
    ELSE
        RAISE NOTICE 'Dropping schema % cascading...', p_schema_name;
        EXECUTE 'drop schema ' || p_schema_name || ' cascade';
        RAISE NOTICE 'Dropped SUCCESSFULLY ';
    END IF;

    RETURN;


END;
$BODY$ LANGUAGE plpgsql SECURITY INVOKER;