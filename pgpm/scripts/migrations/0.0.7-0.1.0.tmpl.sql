/*
    Migration script from version 0.7.0 to 0.1.0 (or higher if tool doesn't find other migration scripts)
 */
DROP FUNCTION IF EXISTS {schema_name}._add_package_info(TEXT, TEXT, INTEGER, INTEGER, INTEGER, INTEGER, TEXT, TEXT, TEXT, TEXT, INTEGER[], TEXT);