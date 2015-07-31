#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Deployment script that will deploy Postgres schemas to a given DB
Copyright (c) Affinitas GmbH

Usage:
  pgpm deploy <connection_string> [-m | --mode <mode>]
                [-o | --owner <owner_role>] [-u | --user <user_role>...]
                [-f <file_name>...] [--add-config <config_file_path>]
                [--full-path] [--debug-mode]
                [--vcs-ref <vcs_reference>] [--vcs-link <vcs_link>]
                [--issue-ref <issue_reference>] [--issue-link <issue_link>]
  pgpm remove <connection_string> --pkg-name <schema_name> <v_major> <v_minor> <v_patch> <v_pre> [--old-rev <old_rev>]
  pgpm install <connection_string> [--update]
  pgpm uninstall <connection_string>
  pgpm -h | --help
  pgpm -v | --version

Arguments:
  <connection_string>       Connection string to postgres database.
                            Can be in any format psycopg2 would understand it
  <v_major>                 Major part of version of package
  <v_minor>                 Minor part of version of package
  <v_patch>                 Patch part of version of package
  <v_pre>                   Pre part of version of package

Options:
  -h --help                 Show this screen.
  -v --version              Show version.
  -f <file_name>..., --file <file_name>...
                            Use it if you want to deploy only specific files (functions, types, etc).
                            In that case these files if exist will be overridden.
                            Should be followed by the list of names of files to deploy.
  --full-path               By file deployment will take <file_name> as full relative path and only as file name
  -o <owner_role>, --owner <owner_role>
                            Role to which schema owner will be changed. User connecting to DB
                            needs to be a superuser. If omitted, user running the script
                            will the owner of schema
  -u <user_role>..., --user <user_role>...
                            Roles to which GRANT USAGE privilege will be applied.
                            If omitted, default behaviour of DB applies
  -m <mode>, --mode <mode>  Deployment mode. Can be:
                            * safe. Add constraints to deployment. Will not deploy schema
                            if it already exists in the DB
                            * moderate. If schema exists, will try to rename it by adding suffix "_"
                            and deploy new schema with old name
                            * unsafe. allows cascade deleting of schema if it exists and adding new one
                            [default: safe]
                            * overwrite. Will run scripts overwriting existing ones.
                            User have to make sure that overwriting is possible.
                            E.g. if type exists, rewriting should be preceeded with dropping it first manually
  --add-config <config_file_path>
                            Provides path to additional config file. Attributes of this file overwrite config.json
  --debug-mode              Debug level loggin enabled if command is present. Otherwise Info level
  --update                  Update pgpm to a newer version
  --vcs-ref <vcs_reference> Adds vcs reference to deployments log table
  --vcs-link <vcs_link>
                            Adds link to repository to deployments log table
  --issue-ref <issue_reference>
                            Adds issue reference to deployments log table
  --issue-link <issue_link> Adds link to issue tracking system to deployments log table
  --pkg-name <schema_name>  Package name to be removed
  --old-rev <old_rev>       If omitted all old revisions are deleted together with current revision.
                            If specified just the specified revision is deleted


"""
import logging

import os
import psycopg2
import json
import sqlparse
import re
import sys
import io
import pkgutil
import pkg_resources

from pgpm.utils import config, vcs

from pgpm import _version, _variables
from docopt import docopt
from distutils import version

SET_SEARCH_PATH = "SET search_path TO {0}, public;"

# getting logging
logger = logging.getLogger(__name__)

def connect_db(connection_string):
    """
    Connect to DB or exit on exception
    """
    logger.info('Connecting to databases for deployment...')
    conn = psycopg2.connect(connection_string)
    cur = conn.cursor()
    logger.info('Connected to {0}'.format(connection_string))

    return conn, cur


def close_db_conn(cur, conn, conn_string):
    """
    Close DB connection and cursor
    """
    logger.info('Closing connection to {0}...'.format(conn_string))
    cur.close()
    conn.close()
    logger.info('Connection to {0} closed.'.format(conn_string))


def schema_exists(cur, schema_name):
    """
    Check if schema exists
    """
    cur.execute("SELECT EXISTS (SELECT schema_name FROM information_schema.schemata WHERE schema_name = '{0}');"
                .format(schema_name))
    return cur.fetchone()[0]


def create_db_schema(cur, schema_name, users, owner):
    """
    Create Postgres schema script and execute it on cursor
    """
    _create_schema_script = "CREATE SCHEMA {0} ;\n".format(schema_name)
    if users:
        _create_schema_script += "GRANT USAGE ON SCHEMA {0} TO {1};\n".format(schema_name, ", ".join(users))
    if owner:
        _create_schema_script += "ALTER SCHEMA {0} OWNER TO {1};\n".format(schema_name, owner)
    _create_schema_script += SET_SEARCH_PATH.format(schema_name)
    cur.execute(_create_schema_script)
    logger.info('Schema {0} was created and search_path was changed.'.format(schema_name))


def find_whole_word(w):
    """
    Finds whole word
    """
    return re.compile(r'\b({0})\b'.format(w), flags=re.IGNORECASE).search


def collect_scripts_from_files(script_paths, files_deployment, is_package=False, is_full_path=False):
    """
    Collects postgres scripts from source files
    """
    script_files_count = 0
    script = ''
    if script_paths:
        if not isinstance(script_paths, list):
            script_paths = [script_paths]
        if files_deployment:  # if specific script to be deployed, only find them
            if is_full_path:
                for list_file_name in files_deployment:
                    if os.path.isfile(list_file_name):
                        for i in range(len(script_paths)):
                            if script_paths[i] in list_file_name:
                                script_files_count += 1
                                script += io.open(list_file_name, 'r', -1, 'utf-8-sig').read()
                                script += '\n'
                                logger.info('{0}'.format(list_file_name))
                    else:
                        logger.warning('File {0} does not exist, please specify a correct path'
                                       .format(list_file_name))
            else:
                for script_path in script_paths:
                    for subdir, dirs, files in os.walk(script_path):
                        logger.debug('{0} {1}'.format(subdir, dirs))
                        for file_info in files:
                            for list_file_name in files_deployment:
                                # if subdir in files_deployment:
                                #     if file_info == list_file_name
                                if file_info == list_file_name:
                                    script_files_count += 1
                                    script += io.open(os.path.join(subdir, file_info), 'r', -1, 'utf-8-sig').read()
                                    script += '\n'
                                    logger.info('{0}'.format(os.path.join(subdir, file_info)))
        else:
            if is_package:
                for script_path in script_paths:
                    logger.debug('{0}'.format(script_path))
                    for file_info in pkg_resources.resource_listdir(__name__, script_path):
                        script_files_count += 1
                        script += pkg_resources.resource_string(__name__, '{0}/{1}'.format(script_path, file_info))\
                            .decode('utf-8')
                        script += '\n'
                        logger.info('{0}/{1}'.format(script_path, file_info))
            else:
                for script_path in script_paths:
                    for subdir, dirs, files in os.walk(script_path):
                        logger.debug('{0} {1}'.format(subdir, dirs))
                        for file_info in files:
                            if file_info != _variables.CONFIG_FILE_NAME:
                                script_files_count += 1
                                script += io.open(os.path.join(subdir, file_info), 'r', -1, 'utf-8-sig').read()
                                script += '\n'
                                logger.info('{0}'.format(os.path.join(subdir, file_info)))
    return script, script_files_count


def get_scripts(path_parameter, config_data, files_deployment, script_type, is_full_path=False):
    """
    Gets scripts from specified folders
    """

    if path_parameter in config_data:
        path_value = config_data[path_parameter]
    else:
        path_value = None

    logger.info('Getting scripts with {0} definitions'.format(script_type))
    script, files_count = collect_scripts_from_files(path_value, files_deployment, False, is_full_path)
    if path_value:
        if files_count == 0:
            logger.warning('No {0} definitions were found in {1} folder'.format(script_type, path_value))
    else:
        logger.info('No {0} folder was specified'.format(script_type))

    return script, files_count


def reorder_types(types_script):
    """
    Takes type scripts and reorders them to avoid Type doesn't exist exception
    """
    logger.info('Running types definitions scripts')
    logger.info('Reordering types definitions scripts to avoid "type does not exist" exceptions')
    _type_statements = sqlparse.split(types_script)
    # TODO: move up to classes
    _type_statements_dict = {}  # dictionary that store statements with type and order.
    type_unordered_scripts = []  # scripts to execute without order
    type_drop_scripts = []  # drop scripts to execute first
    for _type_statement in _type_statements:
        _type_statement_parsed = sqlparse.parse(_type_statement)
        if len(_type_statement_parsed) > 0:  # can be empty parsed object so need to check
            # we need only type declarations to be ordered
            if _type_statement_parsed[0].get_type() == 'CREATE':
                _type_body_r = r'\bcreate\s+\b(?:type|domain)\s+\b(\w+\.\w+|\w+)\b'
                _type_name = re.compile(_type_body_r, flags=re.IGNORECASE).findall(_type_statement)[0]
                _type_statements_dict[str(_type_name)] = \
                    {'script': _type_statement, 'deps': []}
            elif _type_statement_parsed[0].get_type() == 'DROP':
                type_drop_scripts.append(_type_statement)
            else:
                type_unordered_scripts.append(_type_statement)
    # now let's add dependant types to dictionary with types
    _type_statements_list = []  # list of statements to be ordered
    for _type_key in _type_statements_dict.keys():
        for _type_key_sub, _type_value in _type_statements_dict.items():
            if _type_key != _type_key_sub:
                if find_whole_word(_type_key)(_type_value['script']):
                    _type_value['deps'].append(_type_key)
    # now let's add order to type scripts and put them ordered to list
    _deps_unresolved = True
    _type_script_order = 0
    _type_names = []
    type_ordered_scripts = []  # ordered list with scripts to execute
    while _deps_unresolved:
        for k, v in _type_statements_dict.items():
            if not v['deps']:
                _type_names.append(k)
                v['order'] = _type_script_order
                _type_script_order += 1
                if not v['script'] in type_ordered_scripts:
                    type_ordered_scripts.append(v['script'])
            else:
                _dep_exists = True
                for _dep in v['deps']:
                    if _dep not in _type_names:
                        _dep_exists = False
                if _dep_exists:
                    _type_names.append(k)
                    v['order'] = _type_script_order
                    _type_script_order += 1
                    if not v['script'] in type_ordered_scripts:
                        type_ordered_scripts.append(v['script'])
                else:
                    v['order'] = -1
        _deps_unresolved = False
        for k, v in _type_statements_dict.items():
            if v['order'] == -1:
                _deps_unresolved = True
    return type_drop_scripts, type_ordered_scripts, type_unordered_scripts


def resolve_dependencies(cur, dependencies):
    """
    Function checks if dependant packages are installed in DB
    """
    list_of_deps_ids = []
    _list_of_deps_unresolved = []
    _is_deps_resolved = True
    for k, v in dependencies.items():
        cur.execute(SET_SEARCH_PATH.format(_variables.PGPM_SCHEMA_NAME))
        cur.execute("SELECT {0}._find_schema('{1}', '{2}')"
                    .format(_variables.PGPM_SCHEMA_NAME, k, v))
        pgpm_v_ext = tuple(cur.fetchone()[0][1:-1].split(','))
        try:
            list_of_deps_ids.append(int(pgpm_v_ext[0]))
        except:
            pass
        if not pgpm_v_ext[0]:
            _is_deps_resolved = False
            _list_of_deps_unresolved.append("{0}: {1}".format(k, v))

    return _is_deps_resolved, list_of_deps_ids, _list_of_deps_unresolved


def install_manager(arguments):
    """
    Installs package manager
    """
    conn, cur = connect_db(arguments['<connection_string>'])

    # get pgpm functions
    script, files_count = collect_scripts_from_files('scripts/functions', False, True, True)

    # Create schema if it doesn't exist
    if schema_exists(cur, _variables.PGPM_SCHEMA_NAME):
        # Executing pgpm functions
        if files_count > 0:
            logger.info('Running functions definitions scripts')
            logger.debug(script)
            cur.execute(SET_SEARCH_PATH.format(_variables.PGPM_SCHEMA_NAME))
            cur.execute(script)
            logger.info('Functions loaded to schema {0}'.format(_variables.PGPM_SCHEMA_NAME))
        else:
            logger.info('No function scripts to deploy')

        conn.commit()

        # check installed version of _pgpm schema.
        pgpm_v_db_tuple = _get_pgpm_installed_v(cur)
        pgpm_v_db = version.StrictVersion(".".join(pgpm_v_db_tuple))
        pgpm_v_script = version.StrictVersion(_version.__version__)
        if pgpm_v_script > pgpm_v_db:
            if arguments['--update']:
                _migrate_pgpm_version(cur, conn, arguments['<connection_string>'], True)
            else:
                _migrate_pgpm_version(cur, conn, arguments['<connection_string>'], False)
        elif pgpm_v_script < pgpm_v_db:
            logger.error('Deployment script\'s version is lower than the version of {0} schema '
                         'installed in DB. Update pgpm script first.'.format(_variables.PGPM_SCHEMA_NAME))
            close_db_conn(cur, conn, arguments['<connection_string>'])
            sys.exit(1)
        else:
            logger.error('Can\'t install pgpm as schema {0} already exists'.format(_variables.PGPM_SCHEMA_NAME))
            close_db_conn(cur, conn, arguments['<connection_string>'])
            sys.exit(1)
    else:
        # Prepare and execute preamble
        _deployment_script_preamble = pkgutil.get_data('pgpm', 'scripts/deploy_prepare_config.sql')
        logger.info('Executing a preamble to install statement')
        cur.execute(_deployment_script_preamble)

        # Python 3.x doesn't have format for byte strings so we have to convert
        _install_script = pkgutil.get_data('pgpm', 'scripts/install.tmpl.sql').decode('utf-8')
        logger.info('Installing package manager')
        cur.execute(_install_script.format(schema_name=_variables.PGPM_SCHEMA_NAME))

        # Executing pgpm functions
        if files_count > 0:
            logger.info('Running functions definitions scripts')
            logger.debug(script)
            cur.execute(SET_SEARCH_PATH.format(_variables.PGPM_SCHEMA_NAME))
            cur.execute(script)
            logger.info('Functions loaded to schema {0}'.format(_variables.PGPM_SCHEMA_NAME))
        else:
            logger.info('No function scripts to deploy')

        conn.commit()

    cur.execute(SET_SEARCH_PATH.format(_variables.PGPM_SCHEMA_NAME))
    cur.callproc('{0}._upsert_package_info'.format(_variables.PGPM_SCHEMA_NAME),
                 [_variables.PGPM_SCHEMA_NAME, _variables.PGPM_SCHEMA_SUBCLASS,
                  _variables.PGPM_VERSION.major, _variables.PGPM_VERSION.minor, _variables.PGPM_VERSION.patch,
                  _variables.PGPM_VERSION.pre, _variables.PGPM_VERSION.metadata,
                  'Package manager for Postgres', 'MIT'])
    # Commit transaction
    conn.commit()

    close_db_conn(cur, conn, arguments['<connection_string>'])


def deployment_manager(arguments):
    """
    Deploys schema
    :param arguments: params from cli
    :return:
    """

    user_roles = arguments['--user']
    if arguments['--owner']:
        owner_role = arguments['--owner'][0]
    else:
        owner_role = ''
    files_deployment = arguments['--file']  # if specific script to be deployed, only find them
    is_full_path = arguments['--full-path']

    # Load project configuration file
    logger.info('Loading project configuration...')
    config_json = open(_variables.CONFIG_FILE_NAME)
    config_data = json.load(config_json)
    config_json.close()
    if arguments['--add-config']:
        logger.info('Adding additional configuration file {0}'.format(arguments['--add-config']))
        add_config_json = open(arguments['--add-config'])
        config_data = dict(list(config_data.items()) + list(json.load(add_config_json).items()))
        add_config_json.close()
    config_obj = config.SchemaConfiguration(config_data)

    # Check if in git repo
    vcs_ref = None
    vcs_link = None
    issue_ref = None
    issue_link = None
    if arguments['--vcs-ref']:
        vcs_ref = arguments['--vcs-ref']
    else:
        if vcs.is_git_directory():
            vcs_ref = vcs.get_git_revision_hash()
            logger.debug('commit reference to be deployed is {0}'.format(vcs_ref))
        else:
            logger.info('Folder is not a known vcs repository')
    if arguments['--vcs-link']:
        vcs_link = arguments['--vcs-link']
    if arguments['--issue-ref']:
        issue_ref = arguments['--issue-ref']
    if arguments['--issue-link']:
        issue_link = arguments['--issue-link']

    # Check if owner role and user roles are to be defined with config files
    if not owner_role and config_obj.owner_role:
        owner_role = config_obj.owner_role
    if not user_roles and config_obj.user_roles:
        user_roles = config_obj.user_roles

    logger.info('Configuration of project {0} of version {1} loaded successfully.'
                .format(config_obj.name, config_obj.version.raw))  # TODO: change to to_string once discussed
    # .format(config_obj.name, config_obj.version.to_string()))

    # Get scripts
    types_script, types_files_count = get_scripts("types_path", config_data, files_deployment, "types", is_full_path)
    functions_script, functions_files_count = get_scripts("functions_path", config_data, files_deployment,
                                                          "functions", is_full_path)
    views_script, views_files_count = get_scripts("views_path", config_data, files_deployment, "views", is_full_path)
    triggers_script, triggers_files_count = get_scripts("triggers_path", config_data, files_deployment, "triggers",
                                                        is_full_path)
    tables_script, tables_files_count = get_scripts("tables_path", config_data, files_deployment, "tables",
                                                    is_full_path)

    # Connect to DB
    conn, cur = connect_db(arguments['<connection_string>'])
    # Check if DB is pgpm enabled
    if not schema_exists(cur, _variables.PGPM_SCHEMA_NAME):
        logger.error('Can\'t deploy schemas to DB where pgpm was not installed. '
                     'First install pgpm by running pgpm install')
        close_db_conn(cur, conn, arguments['<connection_string>'])
        sys.exit(1)

    # check installed version of _pgpm schema.
    pgpm_v_db_tuple = _get_pgpm_installed_v(cur)
    pgpm_v_db = version.StrictVersion(".".join(pgpm_v_db_tuple))
    pgpm_v_script = version.StrictVersion(_version.__version__)
    if pgpm_v_script > pgpm_v_db:
        _migrate_pgpm_version(cur, conn, arguments['<connection_string>'], False)
    elif pgpm_v_script < pgpm_v_db:
        logger.error('Deployment script\'s version is lower than the version of {0} schema '
                     'installed in DB. Update pgpm script first.'.format(_variables.PGPM_SCHEMA_NAME))
        close_db_conn(cur, conn, arguments['<connection_string>'])
        sys.exit(1)

    # Resolve dependencies
    list_of_deps_ids = []
    if hasattr(config_obj, 'dependencies'):
        _is_deps_resolved, list_of_deps_ids, _list_of_unresolved_deps = \
            resolve_dependencies(cur, config_obj.dependencies)
        if not _is_deps_resolved:
            logger.error('There are unresolved dependencies. Deploy the following package(s) and try again:')
            for unresolved_pkg in _list_of_unresolved_deps:
                logger.error('{0}'.format(unresolved_pkg))
            close_db_conn(cur, conn, arguments['<connection_string>'])
            sys.exit(1)

    # Prepare and execute preamble
    _deployment_script_preamble = pkgutil.get_data('pgpm', 'scripts/deploy_prepare_config.sql')
    logger.info('Executing a preamble to deployment statement')
    logger.debug(_deployment_script_preamble)
    cur.execute(_deployment_script_preamble)

    # Get schema name from project configuration
    schema_name = ''
    if config_obj.subclass == 'versioned':
        schema_name = '{0}_{1}'.format(config_obj.name, config_obj.version.raw)

        logger.info('Schema {0} will be updated'.format(schema_name))
    elif config_obj.subclass == 'basic':
        schema_name = '{0}'.format(config_obj.name)
        if not arguments['--file']:
            logger.info('Schema {0} will be created/replaced'.format(schema_name))
        else:
            logger.info('Schema {0} will be updated'.format(schema_name))

    # Create schema or update it if exists (if not in production mode) and set search path
    if arguments['--file']:  # if specific scripts to be deployed
        if not schema_exists(cur, schema_name):
            logger.error('Can\'t deploy scripts to schema {0}. Schema doesn\'t exist in database'.format(schema_name))
            close_db_conn(cur, conn, arguments.get('<connection_string>'))
            sys.exit(1)
        else:
            _set_search_path_schema_script = SET_SEARCH_PATH.format(schema_name)
            cur.execute(_set_search_path_schema_script)
            logger.info('Search_path was changed to schema {0}'.format(schema_name))
    else:
        if not schema_exists(cur, schema_name):
            create_db_schema(cur, schema_name, user_roles, owner_role)
        elif arguments['--mode'][0] == 'safe':
            logger.error('Schema already exists. It won\'t be overriden in safe mode. '
                         'Rerun your script without "-m moderate" or "-m unsafe" flags')
            close_db_conn(cur, conn, arguments.get('<connection_string>'))
            sys.exit(1)
        elif arguments['--mode'][0] == 'moderate':
            _old_schema_exists = True
            _old_schema_rev = 0
            while _old_schema_exists:
                cur.execute("SELECT EXISTS (SELECT schema_name FROM information_schema.schemata "
                            "WHERE schema_name = '{0}');".format(schema_name + '_' + str(_old_schema_rev)))
                _old_schema_exists = cur.fetchone()[0]
                if _old_schema_exists:
                    _old_schema_rev += 1
            _old_schema_name = schema_name + '_' + str(_old_schema_rev)
            logger.info('Schema already exists. It will be renamed to {0} in moderate mode. Renaming...'
                        .format(_old_schema_name))
            _rename_schema_script = "ALTER SCHEMA {0} RENAME TO {1};\n".format(schema_name, _old_schema_name)
            cur.execute(_rename_schema_script)
            # Add metadata to pgpm schema
            cur.execute(SET_SEARCH_PATH.format(_variables.PGPM_SCHEMA_NAME))
            cur.callproc('{0}._set_revision_package'.format(_variables.PGPM_SCHEMA_NAME),
                         [config_obj.name,
                          config_obj.subclass,
                          _old_schema_rev,
                          config_obj.version.major,
                          config_obj.version.minor,
                          config_obj.version.patch,
                          config_obj.version.pre])
            logger.info('Schema {0} was renamed to {1}. Meta info was added to {2} schema'
                        .format(schema_name, _old_schema_name, _variables.PGPM_SCHEMA_NAME))
            create_db_schema(cur, schema_name, user_roles, owner_role)
        elif arguments['--mode'][0] == 'unsafe':
            _drop_schema_script = "DROP SCHEMA {0} CASCADE;\n".format(schema_name)
            cur.execute(_drop_schema_script)
            logger.info('Dropping old schema {0}'.format(schema_name))
            create_db_schema(cur, schema_name, user_roles, owner_role)

    # Executing DDL scripts
    # if ddl_files_count > 0:
    #     logger.info('Running DDL scripts')
    #     # print(TermStyle.HEADER + functions_script)
    #     cur.execute(ddl_script)
    #     logger.info('DDL executed for schema {0}'.format(schema_name))
    # else:
    #     logger.info('No DDL scripts to execute')

    # Reordering and executing types
    if types_files_count > 0:
        type_drop_scripts, type_ordered_scripts, type_unordered_scripts = reorder_types(types_script)
        logger.debug(type_ordered_scripts)
        if type_drop_scripts:
            cur.execute('\n'.join(type_drop_scripts))
        if type_ordered_scripts:
            cur.execute('\n'.join(type_ordered_scripts))
        if type_unordered_scripts:
            cur.execute('\n'.join(type_unordered_scripts))
        logger.info('Types loaded to schema {0}'.format(schema_name))
    else:
        logger.info('No type scripts to deploy')

    # Executing functions
    if functions_files_count > 0:
        logger.info('Running functions definitions scripts')
        logger.debug(functions_script)
        cur.execute(functions_script)
        logger.info('Functions loaded to schema {0}'.format(schema_name))
    else:
        logger.info('No function scripts to deploy')

    # Executing views
    if views_files_count > 0:
        logger.info('Running views definitions scripts')
        logger.debug(views_script)
        cur.execute(views_script)
        logger.info('Views loaded to schema {0}'.format(schema_name))
    else:
        logger.info('No view scripts to deploy')

    # Executing tables
    if tables_files_count > 0:
        logger.warning('Support for DDL or data updates is not implemented yet')
    else:
        logger.info('No DDL or data update scripts to deploy')

    # Executing triggers
    if triggers_files_count > 0:
        logger.info('Running views definitions scripts')
        logger.debug(triggers_script)
        cur.execute(triggers_script)
        logger.info('Views loaded to schema {0}'.format(schema_name))
    else:
        logger.info('No view scripts to deploy')

    # Add metadata to pgpm schema
    cur.execute(SET_SEARCH_PATH.format(_variables.PGPM_SCHEMA_NAME))
    cur.callproc('{0}._upsert_package_info'.format(_variables.PGPM_SCHEMA_NAME),
                 [config_obj.name,
                  config_obj.subclass,
                  config_obj.version.major,
                  config_obj.version.minor,
                  config_obj.version.patch,
                  config_obj.version.pre,
                  config_obj.version.metadata,
                  config_obj.description,
                  config_obj.license,
                  list_of_deps_ids,
                  vcs_ref,
                  vcs_link,
                  issue_ref,
                  issue_link])
    logger.info('Meta info about deployment was added to schema {0}'
                .format(_variables.PGPM_SCHEMA_NAME))

    # Commit transaction
    conn.commit()

    close_db_conn(cur, conn, arguments.get('<connection_string>'))


def _get_pgpm_installed_v(cur):
    """
    returns current version of pgpm schema
    :return:
    """
    cur.execute(SET_SEARCH_PATH.format(_variables.PGPM_SCHEMA_NAME))
    cur.execute("SELECT {0}._find_schema('{1}', '{2}')"
                .format(_variables.PGPM_SCHEMA_NAME, _variables.PGPM_SCHEMA_NAME, 'x'))
    pgpm_v_ext = tuple(cur.fetchone()[0][1:-1].split(','))

    return pgpm_v_ext[2], pgpm_v_ext[3], pgpm_v_ext[4]


def _migrate_pgpm_version(cur, conn, connection_string, migrate_or_leave):
    """
    Enact migration script from one version of pgpm to another (newer)
    :param cur:
    :param migrate_or_leave: True if migrating, False if exiting
    :return:
    """
    migrations_file_re = r'^(.*)-(.*).tmpl.sql$'
    version_pgpm_db_tuple = _get_pgpm_installed_v(cur)
    version_pgpm_db = version.StrictVersion(".".join(version_pgpm_db_tuple))
    version_pgpm_script = version.StrictVersion(_version.__version__)
    for file_info in pkg_resources.resource_listdir(__name__, 'scripts/migrations/'):
        versions_list = re.compile(migrations_file_re, flags=re.IGNORECASE).findall(file_info)
        version_a = version.StrictVersion(versions_list[0][0])
        version_b = version.StrictVersion(versions_list[0][1])
        if version_pgpm_script >= version_a and version_b > version_pgpm_db:
            # Python 3.x doesn't have format for byte strings so we have to convert
            migration_script = pkg_resources.resource_string(__name__, 'scripts/migrations/{0}'.format(file_info))\
                .decode('utf-8').format(schema_name=_variables.PGPM_SCHEMA_NAME)
            if migrate_or_leave:
                logger.info('Running version upgrade script {0}'.format(file_info))
                logger.debug(migration_script)
                cur.execute(migration_script)
                conn.commit()
                cur.execute(SET_SEARCH_PATH.format(_variables.PGPM_SCHEMA_NAME))
                cur.callproc('{0}._add_migration_info'.format(_variables.PGPM_SCHEMA_NAME),
                             [versions_list[0][0], versions_list[0][1]])
                conn.commit()
                logger.info('Successfully finished running version upgrade script {0}'
                            .format(file_info))
            else:
                logger.error('{0} schema version is outdated. Please run pgpm install --upgrade first.'
                             .format(_variables.PGPM_SCHEMA_NAME))
                close_db_conn(cur, conn, connection_string)
                sys.exit(1)


def main():
    arguments = docopt(__doc__, version=_version.__version__)

    # setting logging
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if arguments['--debug-mode']:
        logger_level = logging.DEBUG
    else:
        logger_level = logging.INFO
    logger.setLevel(logger_level)
    handler = logging.StreamHandler()
    handler.setLevel(logger_level)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if arguments['install']:
        install_manager(arguments)
    elif arguments['deploy']:
        deployment_manager(arguments)
    else:
        print(arguments)

if __name__ == '__main__':
    main()
