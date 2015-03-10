CREATE OR REPLACE FUNCTION _add_package_info(p_pkg_name varchar(255),
                                             p_pkg_subclass_name varchar(255),
                                             p_pkg_old_rev integer,
                                             p_pkg_v_major integer,
                                             p_pkg_v_minor integer DEFAULT 0,
                                             p_pkg_v_patch integer DEFAULT 0,
                                             p_pkg_v_pre varchar(255) DEFAULT NULL,
                                             p_pkg_v_metadata varchar(255) DEFAULT NULL,
                                             p_pkg_description text DEFAULT '',
                                             p_pkg_license text DEFAULT NULL,
                                             p_pkg_vcs_ref varchar(255) DEFAULT NULL)
    RETURNS integer AS
$BODY$
---
-- @description
-- Adds package info to pgpm package info table
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
-- @param p_pkg_vcs_ref
-- vcs reference to track the code
---
DECLARE
    l_existing_pkg_id integer;

	return_value integer;
BEGIN

    -- Case 1: unsafe mode, rewrite of the whole schema with the same version or some of the files in it
    -- Case 2: new schema with new version
    -- Case 3: moderate mode, adding old revision number

    IF p_pkg_old_rev IS NULL THEN -- Case 1 and 2
        SELECT pkg_id INTO l_existing_pkg_id
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
    ELSE -- Case 3
        SELECT pkg_id INTO l_existing_pkg_id
        FROM packages
        WHERE pkg_name = p_pkg_name
            AND pkg_subclass IN (SELECT pkg_sc_id
                                 FROM package_subclasses
                                 WHERE pkg_sc_name = p_pkg_subclass_name)
            AND pkg_v_major = p_pkg_v_major
            AND (pkg_v_minor IS NULL OR pkg_v_minor = p_pkg_v_minor)
            AND (pkg_v_patch IS NULL OR pkg_v_patch = p_pkg_v_patch)
            AND (pkg_v_pre IS NULL OR pkg_v_pre = p_pkg_v_pre)
            AND (pkg_old_rev = p_pkg_old_rev);
    END IF;

    IF FOUND THEN -- Case 1:
        UPDATE packages
        SET pkg_last_modified = now()
        WHERE pkg_id = l_existing_pkg_id;
    ELSE -- Case 2 and 3:
        INSERT INTO packages (
            pkg_name,
            pkg_description,
            pkg_v_major,
            pkg_v_minor,
            pkg_v_patch,
            pkg_v_pre,
            pkg_v_metadata,
            pkg_old_rev,
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
            p_pkg_old_rev,
            pkg_sc_id,
            p_pkg_license
        FROM package_subclasses WHERE pkg_sc_name = p_pkg_subclass_name
        RETURNING
            pkg_id
        INTO return_value;
    END IF;

    RETURN return_value;
END;
$BODY$
    LANGUAGE 'plpgsql' VOLATILE SECURITY DEFINER
    COST 30;
