CREATE OR REPLACE FUNCTION _add_migration_info(p_m_low_v TEXT, p_m_high_v TEXT)
    RETURNS VOID AS
$BODY$
---
-- @description
-- Adds migration info migrations log table
--
-- @param p_m_low_v
-- lower border of version that is applicaple for this migration
--
-- @param p_m_high_v
-- package type: either version (with version suffix at the end of the name) or basic (without)
--
-- @param p_pkg_old_rev
-- higher border of version that is applicaple for this migration
--
---
BEGIN

    INSERT INTO migrations_log (m_low_v, m_high_v)
        VALUES (p_m_low_v, p_m_high_v);
END;
$BODY$
LANGUAGE 'plpgsql' VOLATILE SECURITY DEFINER;
