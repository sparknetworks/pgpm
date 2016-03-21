-- =============================
-- Test Case : drop_schema_smart
-- =============================

-- ================
-- Preparation step
-- ================

create schema IF NOT EXISTS test_case_ds1;
create schema IF NOT EXISTS test_case_ds2;
create schema IF NOT EXISTS test_case_ds3;

CREATE TYPE test_case_ds1.dep_type1 AS (x text);
CREATE TYPE test_case_ds2.ref_type1 AS (y test_case_ds1.dep_type1);
CREATE TYPE test_case_ds3.simple_type1 AS (z text);

create table IF NOT EXISTS test_case_ds1.dep_tab1 ( a integer);
create table IF NOT EXISTS test_case_ds2.ref_tab1 ( b test_case_ds1.dep_type1);

create or replace function test_case_ds2.ref_func(z test_case_ds1.dep_type1) RETURNS integer AS $BODY$ BEGIN return 1; END;$BODY$ LANGUAGE PLPGSQL;
create or replace function test_case_ds3.func_sleep(sec_sleep integer) RETURNS void AS $BODY$ BEGIN perform pg_sleep(sec_sleep); END;$BODY$ LANGUAGE PLPGSQL;


-- ======================
-- Test Case : Excecution
-- ======================


-- =====================================
-- Test Case : nonexistent Schema
-- =====================================
select drop_schema_smart('no_such_schema');
-- expected result : Nächster
--	Output message : ERROR:  message: Schema no_such_schema does not exist


-- ============================================
-- Test Case : contains tables
-- ============================================
select drop_schema_smart('test_case_ds2',false);
-- expected result :
--	Output message : ERROR:  message: Schema contains at least one table!


-- ============================
-- Test Case : currently in use
-- ============================
select test_case_ds3.func_sleep(120); --run from different session ;
select drop_schema_smart('test_case_ds3',false); --run from current session
-- expected result :
--	Output message : ERROR:  message: Schema test_case_ds3 currently in use


-- ===================
-- Test Case : Dry Run
-- ===================
select drop_schema_smart('test_case_ds3');
-- expected result :
--	Output messageses : All checks are ok, last message : THIS IS THE DRY RUN. TO DROP SCHEMA test_case_ds3 PASS FALSE TO DRY RUN PARAMETER



-- ==============================
-- Test Case : Check dependencies
-- ==============================
drop table if exists test_case_ds1.dep_tab1;
select drop_schema_smart('test_case_ds1',false);
-- expected result :
--	Output messageses : ERROR:  message: Schema has type dependencies with other schemas, please contact DBA team.


-- ==============================
-- Test Case : Drop Cascade
-- ==============================
drop table if exists test_case_ds2.ref_tab1;
select drop_schema_smart('test_case_ds2',false);
-- expected result :
--	NOTICE:	Dropping schema test_case_ds2 cascading...
--	DETAIL:  drop cascades to type test_case_ds2.ref_type1
--		 drop cascades to function test_case_ds2.ref_func(test_case_ds1.dep_type1)
--	CONTEXT: SQL statement "drop schema test_case_ds2 cascade"
--	NOTICE:  Dropped SUCCESSFULLY


-- ======================
-- Test Case : Clean step
-- ======================
drop schema if exists test_case_ds3 cascade;
drop schema if exists test_case_ds2 cascade;
drop schema if exists test_case_ds1 cascade;