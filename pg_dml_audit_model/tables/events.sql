--
-- journal of all changes to all auditest tables
--
CREATE TABLE events (
  nspname   TEXT        NOT NULL,
  relname   TEXT        NOT NULL,
  usename   TEXT        NOT NULL,
  trans_ts  TIMESTAMPTZ NOT NULL,
  trans_id  BIGINT      NOT NULL,
  trans_sq  INTEGER     NOT NULL,
  operation op_types    NOT NULL,
  rowdata   JSONB,
  CONSTRAINT events_pkey PRIMARY KEY (trans_ts, trans_id, trans_sq)  -- TODO: find optimal order
);

REVOKE ALL ON events FROM PUBLIC;

COMMENT ON TABLE  events IS 'History of auditable actions on audited tables, from audit.if_modified_func()';
COMMENT ON COLUMN events.nspname   IS 'database schema name of the audited table';
COMMENT ON COLUMN events.relname   IS 'name of the table changed by this event';
COMMENT ON COLUMN events.usename   IS 'Session user whose statement caused the audited event'; -- TODO: is this what we need?
COMMENT ON COLUMN events.trans_ts  IS 'Transaction timestamp for tx in which audited event occurred (PK)';
COMMENT ON COLUMN events.trans_id  IS 'Identifier of transaction that made the change. (PK)';
COMMENT ON COLUMN events.trans_sq  IS 'make multi-row-transactions unique. (PK)';
COMMENT ON COLUMN events.operation IS 'event operation of type audit.op_types';
COMMENT ON COLUMN events.rowdata   IS 'Old and new rows affected by this event';

-- ideas for next iteration:
-- COMMENT ON COLUMN audit.events.nodata  IS '''t'' if audit event is from an FOR EACH STATEMENT trigger, ''f'' for FOR EACH ROW';
-- COMMENT ON COLUMN audit.events.query   IS 'Top-level query that caused this auditable event. May be more than one statement.';
-- COMMENT ON COLUMN audit.events.appname IS 'postgres ''application_name'' set when this audit event occurred. Can be changed in-session by client.';


