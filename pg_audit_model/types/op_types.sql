--
-- database operations known to affinitas audit
--
CREATE TYPE op_types AS ENUM ('INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'SNAPSHOT' );

COMMENT ON TYPE op_types IS '
The operation types for audited events. They must include all possible values
of "TG_OP" as listed in the PL/pgSQL trigger documentation
- INSERT   the new row is in rowdata
- UPDATE   both rows go in rowdata OLD first, NEW second
- DELETE   the old row is in rowdata
- TRUCATE  save all rows into rowdata
- SNAPSHOT must be taken when a table has already/still data on start/end of auditing
';



