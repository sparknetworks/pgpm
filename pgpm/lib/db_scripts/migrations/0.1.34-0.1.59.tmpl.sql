/*
    Migration script from version 0.1.34 to 0.1.59 (or higher if tool doesn't find other migration scripts)
 */
DROP FUNCTION IF EXISTS _pgpm.drop_schema_smart(text, boolean);