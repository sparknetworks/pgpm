CREATE OR REPLACE FUNCTION _set_revision_package(p_pkg_name          TEXT,
                                                 p_pkg_subclass_name TEXT,
                                                 p_pkg_old_rev       INTEGER,
                                                 p_pkg_v_major       INTEGER,
                                                 p_pkg_v_minor       INTEGER DEFAULT 0,
                                                 p_pkg_v_patch       INTEGER DEFAULT 0,
                                                 p_pkg_v_pre         TEXT DEFAULT NULL)
    RETURNS INTEGER AS
$BODY$
---
-- @description
-- Set package as old revision, info logged in deployment events table
--
-- @param p_pkg_name
-- package name
--
-- @param p_pkg_subclass_name
-- package type: either version (with version suffix at the end of the name) or basic (without)
--
-- @param p_pkg_old_rev
-- Revision name of package. Used in moderate form. When schema is renamed it is given a revision suffix from here
--
-- @param p_pkg_v_major
-- package major part of version (according to semver)
--
-- @param p_pkg_v_minor
-- package minor part of version (according to semver)
--
-- @param p_pkg_v_patch
-- package patch part of version (according to semver)
--
-- @param p_pkg_v_pre
-- package pre part of version (according to semver)
--
-- @param p_pkg_v_metadata
-- package metadata part of version (according to semver)
--
-- @param p_pkg_vcs_ref
-- vcs reference to track the code
---
DECLARE
    l_existing_pkg_id INTEGER;
    l_pkg_dep_id      INTEGER;

    return_value      INTEGER;
BEGIN

    SELECT pkg_id
    INTO l_existing_pkg_id
    FROM packages
    WHERE pkg_name = p_pkg_name
          AND pkg_subclass IN (SELECT pkg_sc_id
                               FROM package_subclasses
                               WHERE pkg_sc_name = p_pkg_subclass_name)
          AND pkg_v_major = p_pkg_v_major
          AND (pkg_v_minor IS NULL OR pkg_v_minor = p_pkg_v_minor)
          AND (pkg_v_patch IS NULL OR pkg_v_patch = p_pkg_v_patch)
          AND (pkg_v_pre IS NULL OR pkg_v_pre = p_pkg_v_pre);

    IF FOUND
    THEN
        UPDATE packages
        SET pkg_old_rev = p_pkg_old_rev
        WHERE packages.pkg_id = l_existing_pkg_id;

        INSERT INTO deployment_events (dpl_ev_pkg_id, dpl_ev_txid, dpl_ev_vcs_ref, dpl_ev_vcs_link, dpl_ev_issue_id, dpl_ev_issue_link)
            SELECT
                pkg_id,
                txid_current(),
                dpl_ev_vcs_ref,
                dpl_ev_vcs_link,
                dpl_ev_issue_id,
                dpl_ev_issue_link
            FROM packages
                JOIN deployment_events ON dpl_ev_pkg_id = pkg_id
            WHERE pkg_id = l_existing_pkg_id AND dpl_ev_time IN (
                SELECT max(dpl_ev_time)
                FROM deployment_events
                WHERE dpl_ev_pkg_id = packages.pkg_id
            );
    ELSE
        RAISE EXCEPTION 'Package % not found in the list of packages. It could happen if schema exists but wasn''t properly deployed with pgpm',
        p_pkg_name || '_' || p_pkg_v_major || '_' || p_pkg_v_minor || '_' || p_pkg_v_patch;
    END IF;

    -- Notify external channels of successful deployment event
    PERFORM pg_notify('deployment_events' || '$$' || p_pkg_name,
                      p_pkg_v_major || '_' || p_pkg_v_minor || '_' || p_pkg_v_patch);

    RETURN return_value;
END;
$BODY$
LANGUAGE 'plpgsql' VOLATILE SECURITY DEFINER;
