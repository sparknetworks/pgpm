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
                [--issue-ref <issue_reference>] [--issue-link <issue_link>] [--compare-table-scripts-as-int]
                [--log-file <log_file_name>]
  pgpm remove <connection_string> --pkg-name <schema_name> <v_major> <v_minor> <v_patch> <v_pre> [--old-rev <old_rev>]
                [--log-file <log_file_name>]
  pgpm install <connection_string> [--update|--upgrade] [--debug-mode] [-u | --user <user_role>...]
                [--log-file <log_file_name>]
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
  <log_file_name>           Filename for logs

Options:
  -h --help                 Show this screen.
  -v --version              Show version.
  -f <file_name>..., --file <file_name>...
                            Use it if you want to deploy only specific files (functions, types, etc).
                            In that case these files if exist will be overridden.
                            Should be followed by the list of names of files to deploy.
  --full-path               By file deployment will take <file_name> as full relative path and only as file name
  -o <owner_role>, --owner <owner_role>
                            Role to which schema owner and all objects inside will be changed. User connecting to DB
                            needs to be a superuser. If omitted, user running the script
                            will be the owner of schema and all objects inside
                            If --mode flag is *overwrite* or --file flag is used then this is ignored
                            as no new schema is created
  -u <user_role>..., --user <user_role>...
                            Roles to which different usage privileges will be applied.
                            If omitted, default behaviour of DB applies
                            In case used with install command the following will be applied:
                            GRANT SELECT, INSERT, UPDATE, DELETE on all current and future tables
                            GRANT EXECUTE on all future and current functions
                            GRANT USAGE, SELECT on all current and future sequences
                            In case used with deploy command the following will be applied:
                            GRANT USAGE on the schema
                            GRANT EXECUTE on all current functions
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
  --upgrade                  Update pgpm to a newer version
  --vcs-ref <vcs_reference> Adds vcs reference to deployments log table
  --vcs-link <vcs_link>     Adds link to repository to deployments log table
  --issue-ref <issue_reference>
                            Adds issue reference to deployments log table
  --issue-link <issue_link> Adds link to issue tracking system to deployments log table
  --pkg-name <schema_name>  Package name to be removed
  --old-rev <old_rev>       If omitted all old revisions are deleted together with current revision.
                            If specified just the specified revision is deleted
  --compare-table-scripts-as-int
                            Flag says that when table scripts are running they should be ordered
                            but first their names are to be converted to int.
                            By default scripts are ordered by string comparison
  --log-file <log_file_name>
                            Log into a specified file. If not specified, logs are ignored


"""
import logging
import re

import psycopg2

import sqlparse
from docopt import docopt

from pgpm.lib.utils import db
from pgpm import settings


# getting logging
logger = logging.getLogger(__name__)


def connect_db(connection_string):
    """
    Connect to DB or exit on exception
    """
    logger.info('Connecting to databases for deployment...')
    conn = psycopg2.connect(connection_string, connection_factory=db.MegaConnection)
    conn.init(logger)
    cur = conn.cursor()
    logger.info('Connected to {0}'.format(connection_string))

    return conn, cur


def create_db_schema(cur, schema_name):
    """
    Create Postgres schema script and execute it on cursor
    """
    create_schema_script = "CREATE SCHEMA {0} ;\n".format(schema_name)
    create_schema_script += SET_SEARCH_PATH.format(schema_name)
    cur.execute(create_schema_script)
    logger.info('Schema {0} was created and search_path was changed.'.format(schema_name))


def alter_schema_privileges(cur, schema_name, users, owner, process='deployment'):
    """
    Create Postgres schema script and execute it on cursor
    """
    if users:
        if process == 'deployment':
            alter_schema_usage_script = GRANT_USAGE_PRIVILEGES.format(schema_name, ", ".join(users))
            cur.execute(alter_schema_usage_script)
            logger.info('User(s) {0} was (were) granted usage permissions on schema {1}.'
                        .format(", ".join(users), schema_name))
        elif process == 'installation':
            alter_schema_usage_script = GRANT_USAGE_INSTALL_PRIVILEGES.format(schema_name, ", ".join(users))
            cur.execute(alter_schema_usage_script)
            logger.info('User(s) {0} was (were) granted full usage permissions on schema {1}.'
                        .format(", ".join(users), schema_name))
    if owner:
        cur.execute(SET_SEARCH_PATH.format(settings.PGPM_SCHEMA_NAME))
        cur.callproc('_alter_schema_owner', [schema_name, owner])
        logger.info('Ownership of schema {0} and all its objects was changed and granted to user {1}.'
                    .format(schema_name, owner))


def find_whole_word(w):
    """
    Finds whole word
    """
    return re.compile(r'\b({0})\b'.format(w), flags=re.IGNORECASE).search


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
        cur.execute(SET_SEARCH_PATH.format(settings.PGPM_SCHEMA_NAME))
        cur.execute("SELECT {0}._find_schema('{1}', '{2}')"
                    .format(settings.PGPM_SCHEMA_NAME, k, v))
        pgpm_v_ext = tuple(cur.fetchone()[0][1:-1].split(','))
        try:
            list_of_deps_ids.append(int(pgpm_v_ext[0]))
        except:
            pass
        if not pgpm_v_ext[0]:
            _is_deps_resolved = False
            _list_of_deps_unresolved.append("{0}: {1}".format(k, v))

    return _is_deps_resolved, list_of_deps_ids, _list_of_deps_unresolved


def main():
    arguments = docopt(__doc__, version=settings.__version__)

    # setting logging
    formatter = logging.Formatter(settings.LOGGING_FORMATTER)
    if arguments['--debug-mode']:
        logger_level = logging.DEBUG
    else:
        logger_level = logging.INFO
    logger.setLevel(logger_level)
    if arguments['--log-file']:
        handler = logging.FileHandler(arguments['--log-file'])
        handler.setLevel(logger_level)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    if arguments['install']:
        installation_manager =
        install_manager(arguments)
    elif arguments['deploy']:
        deployment_manager(arguments)
    else:
        print(arguments)

if __name__ == '__main__':
    main()
