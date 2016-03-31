
DROP TABLE IF EXISTS ae_c;
DROP FUNCTION IF EXISTS last_modified_before();
DROP TABLE IF EXISTS ae_b;
DROP TABLE IF EXISTS ae_a;


CREATE TABLE ae_a (
  a_text    TEXT PRIMARY KEY,
  a_number  INTEGER,
  a_decimal DECIMAL
);

-- foreign key
CREATE TABLE ae_b (
  a_serial SERIAL PRIMARY KEY,
  a_text   TEXT NOT NULL  REFERENCES ae_a (a_text) ON UPDATE CASCADE ON DELETE RESTRICT,
  a_date   DATE,
  a_time   TIME
);

-- trigger and no primary
CREATE TABLE ae_c (
  test_key         CHARACTER VARYING(128) NOT NULL,
  test_value       TEXT,
  last_modified    TIMESTAMPTZ,
  last_modified_by NAME                   NOT NULL
);

CREATE FUNCTION last_modified_before()
  RETURNS TRIGGER AS $BODY$
DECLARE
BEGIN
  IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE'
  THEN
    NEW.last_modified    := clock_timestamp();
    NEW.last_modified_by := current_user;
  END IF;
  RETURN NEW;
END $BODY$ LANGUAGE plpgsql;

CREATE TRIGGER last_modified_before BEFORE INSERT OR UPDATE ON ae_c FOR EACH ROW
EXECUTE PROCEDURE last_modified_before();

--
-- TODO: add more data types to the test tables
--


