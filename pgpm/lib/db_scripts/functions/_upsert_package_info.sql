CREATE OR REPLACE FUNCTION _upsert_package_info(p_pkg_name          TEXT,
                                                p_pkg_subclass_name TEXT,
                                                p_pkg_v_major       INTEGER,
                                                p_pkg_v_minor       INTEGER DEFAULT 0,
                                                p_pkg_v_patch       INTEGER DEFAULT 0,
                                                p_pkg_v_pre         TEXT DEFAULT NULL,
                                                p_pkg_v_metadata    TEXT DEFAULT NULL,
                                                p_pkg_description   TEXT DEFAULT '',
                                                p_pkg_license       TEXT DEFAULT NULL,
                                                p_pkg_deps_ids      INTEGER [] DEFAULT '{}',
                                                p_pkg_vcs_ref       TEXT DEFAULT NULL,
                                                p_pkg_vcs_link      TEXT DEFAULT NULL,
                                                p_pkg_issue_ref     TEXT DEFAULT NULL,
                                                p_pkg_issue_link    TEXT DEFAULT NULL)
    RETURNS INTEGER AS
$BODY$
---
-- @description
-- Adds package info to pgpm package info table, deployment events table and notifies channels of deployment
--
-- @param p_pkg_name
-- package name
--
-- @param p_pkg_subclass_name
-- package type: either version (with version suffix at the end of the name) or basic (without)
--
-- @param p_pkg_description
-- package description
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
-- @param p_pkg_license
-- package license name/text
--
-- @param p_pkg_deps_ids
-- IDs of dependent schemas
--
-- @param p_pkg_vcs_ref
-- vcs reference to track the code
--
-- @param p_pkg_vcs_link
-- repository link to track the code
--
-- @param p_pkg_issue_ref
-- issue reference to track the code
--
-- @param p_pkg_issue_link
-- issue tracking system link
---
DECLARE
    l_existing_pkg_id INTEGER;
    l_pkg_dep_id      INTEGER;

    return_value      INTEGER;
BEGIN

    -- Case 1: unsafe mode, rewrite of the whole schema with the same version or some of the files in it
    -- Case 2: new schema with new version (safe or moderate modes)

    IF p_pkg_subclass_name = 'basic'
    THEN
        SELECT pkg_id
        INTO l_existing_pkg_id
        FROM packages
        WHERE pkg_name = p_pkg_name
              AND pkg_subclass IN (SELECT pkg_sc_id
                                   FROM package_subclasses
                                   WHERE pkg_sc_name = p_pkg_subclass_name);
    ELSE
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
              AND (pkg_v_pre IS NULL OR pkg_v_pre = p_pkg_v_pre)
              AND pkg_old_rev IS NULL;
    END IF;

    IF FOUND
    THEN -- Case 1:
        DELETE FROM package_dependencies
        WHERE pkg_link_core_id = l_existing_pkg_id;

        FOREACH l_pkg_dep_id IN ARRAY p_pkg_deps_ids
        LOOP
            INSERT INTO package_dependencies (pkg_link_core_id, pkg_link_dep_id)
            VALUES (l_existing_pkg_id, l_pkg_dep_id);
        END LOOP;

        UPDATE packages
        SET pkg_name        = subquery.p_pkg_name,
            pkg_subclass    = subquery.pkg_sc_id,
            pkg_v_major     = subquery.p_pkg_v_major,
            pkg_v_minor     = subquery.p_pkg_v_minor,
            pkg_v_patch     = subquery.p_pkg_v_patch,
            pkg_v_pre       = subquery.p_pkg_v_pre,
            pkg_v_metadata  = subquery.p_pkg_v_metadata,
            pkg_description = subquery.p_pkg_description,
            pkg_license     = subquery.p_pkg_license
        FROM (SELECT
                  p_pkg_name,
                  pkg_sc_id,
                  p_pkg_v_major,
                  p_pkg_v_minor,
                  p_pkg_v_patch,
                  p_pkg_v_pre,
                  p_pkg_v_metadata,
                  p_pkg_description,
                  p_pkg_license
              FROM package_subclasses
              WHERE pkg_sc_name = p_pkg_subclass_name
             ) AS subquery
        WHERE packages.pkg_name = subquery.p_pkg_name;

        INSERT INTO deployment_events (dpl_ev_pkg_id, dpl_ev_txid, dpl_ev_vcs_ref, dpl_ev_vcs_link, dpl_ev_issue_id, dpl_ev_issue_link)
        VALUES (l_existing_pkg_id, txid_current(), p_pkg_vcs_ref, p_pkg_vcs_link, p_pkg_issue_ref, p_pkg_issue_link);

        return_value := l_existing_pkg_id;
    ELSE -- Case 2:
        INSERT INTO packages (
            pkg_name,
            pkg_description,
            pkg_v_major,
            pkg_v_minor,
            pkg_v_patch,
            pkg_v_pre,
            pkg_v_metadata,
            pkg_subclass,
            pkg_license
        )
            SELECT
                p_pkg_name,
                p_pkg_description,
                p_pkg_v_major,
                p_pkg_v_minor,
                p_pkg_v_patch,
                p_pkg_v_pre,
                p_pkg_v_metadata,
                pkg_sc_id,
                p_pkg_license
            FROM package_subclasses
            WHERE pkg_sc_name = p_pkg_subclass_name
        RETURNING
            pkg_id
            INTO return_value;

        FOREACH l_pkg_dep_id IN ARRAY p_pkg_deps_ids
        LOOP
            INSERT INTO package_dependencies (pkg_link_core_id, pkg_link_dep_id) VALUES (return_value, l_pkg_dep_id);
        END LOOP;

        INSERT INTO deployment_events (dpl_ev_pkg_id, dpl_ev_txid, dpl_ev_vcs_ref, dpl_ev_vcs_link, dpl_ev_issue_id, dpl_ev_issue_link)
        VALUES (return_value, txid_current(), p_pkg_vcs_ref, p_pkg_vcs_link, p_pkg_issue_ref, p_pkg_issue_link);

    END IF;

    -- Notify external channels of successful deployment event
    PERFORM pg_notify('deployment_events' || '$$' || p_pkg_name,
                      p_pkg_v_major || '_' || p_pkg_v_minor || '_' || p_pkg_v_patch);

    RETURN return_value;
END;
$BODY$
LANGUAGE 'plpgsql' VOLATILE SECURITY DEFINER;
