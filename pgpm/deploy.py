#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Deployment script that will deploy Postgres schemas to a given DB
Copyright (c) Affinitas GmbH

Usage:
  pgpm deploy <connection_string> [-m | --mode <mode>]
                [-o | --owner <owner_role>] [-u | --user <user_role>...]
                [-f | --file <file_name>...] [--add-config <config_file_path>]
  pgpm install <connection_string>
  pgpm uninstall <connection_string>
  pgpm -h | --help
  pgpm -v | --version

Arguments:
  <connection_string>       Connection string to postgres database.
                            Can be in any format psycopg2 would understand it

Options:
  -h --help                 Show this screen.
  -v --version              Show version.
  -p --production           Add constraints to deployment. Will not deploy versioned schema
                            if it already exists in the DB
  -f <file_name>..., --file <file_name>...
                            Use it if you want to deploy only specific files (functions, types, etc).
                            In that case these files if exist will be overridden.
                            Should be followed by the list of names of files to deploy.
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
  --add-config <config_file_path>
                            Provides path to additional config file. Attributes of this file overwrite config.json

"""

import os
import psycopg2
import json
import sqlparse
import re
import sys
import io
import pkgutil

from pgpm import _version, _variables
from pgpm.utils.term_out_ui import TermStyle
from docopt import docopt


def close_db_conn(cur, conn, conn_string):
    """
    Close DB connection and cursor
    """
    print(TermStyle.PREFIX_INFO + 'Closing connection to {0}...'.format(conn_string))
    cur.close()
    conn.close()
    print(TermStyle.PREFIX_INFO + 'Connection to {0} closed.'.format(conn_string))


def create_db_schema(cur, schema_name, users, owner):
    """
    Create Postgres schema script and execute it on cursor
    """
    _create_schema_script = "CREATE SCHEMA {0} ;\n".format(schema_name)
    if users:
        _create_schema_script += "GRANT USAGE ON SCHEMA {0} TO {1};\n".format(schema_name, ", ".join(users))
    if owner:
        _create_schema_script += "ALTER SCHEMA {0} OWNER TO {1};\n".format(schema_name, owner)
    _create_schema_script += "SET search_path TO {0}, public;".format(schema_name)
    cur.execute(_create_schema_script)
    print(TermStyle.PREFIX_INFO +
          'Schema {0} was created and search_path was changed.'
          .format(schema_name))


def find_whole_word(w):
    """
    Finds whole word
    """
    return re.compile(r'\b({0})\b'.format(w), flags=re.IGNORECASE).search


def collect_scripts_from_files(script_paths, files_deployment):
    """
    Collects postgres scripts from source files
    """
    script_files_count = 0
    script = ''
    if script_paths:
        if not isinstance(script_paths, list):
            script_paths = [script_paths]
        for script_path in script_paths:
            for subdir, dirs, files in os.walk(script_path):
                # print(subdir, dirs)  # uncomment for debugging
                for file_info in files:
                    if files_deployment:  # if specific script to be deployed, only find them
                        for list_file_name in files_deployment:
                            # if subdir in files_deployment:
                            #     if file_info == list_file_name
                            if file_info == list_file_name:
                                script_files_count += 1
                                script += io.open(os.path.join(subdir, file_info), 'r', -1, 'utf-8-sig').read()
                                script += '\n'
                                print(TermStyle.PREFIX_INFO_IMPORTANT + TermStyle.BOLD_ON +
                                      '{0}'.format(os.path.join(subdir, file_info)) + TermStyle.RESET)
                    else:  # if the whole schema to be deployed
                        script_files_count += 1
                        script += io.open(os.path.join(subdir, file_info), 'r', -1, 'utf-8-sig').read()
                        script += '\n'
                        print(TermStyle.PREFIX_INFO_IMPORTANT + TermStyle.BOLD_ON +
                              '{0}'.format(os.path.join(subdir, file_info)) + TermStyle.RESET)
    return script, script_files_count


def get_scripts(path_parameter, config_data, files_deployment, script_type):
    """
    Gets scripts from specified folders
    """
    if path_parameter in config_data:
        path_value = config_data[path_parameter]
    else:
        path_value = None

    print(TermStyle.PREFIX_INFO + 'Getting scripts with {0} definitions'.format(script_type))
    script, files_count = collect_scripts_from_files(path_value, files_deployment)
    if path_value:
        if files_count == 0:
            print(TermStyle.PREFIX_WARNING + 'No {0} definitions were found in {1} folder'.format(script_type, path_value))
    else:
        print(TermStyle.PREFIX_INFO + 'No {0} folder was specified'.format(script_type))

    return script, files_count


def reorder_types(types_script):
    """
    Takes type scripts and reorders them to avoid Type doesn't exist exception
    """
    print(TermStyle.PREFIX_INFO + 'Running types definitions scripts')
    print(TermStyle.PREFIX_INFO + 'Reordering types definitions scripts to avoid "type does not exist" exceptions')
    _type_statements = sqlparse.split(types_script)
    # TODO: move up to classes
    _type_statements_dict = {}  # dictionary that store statements with type and order.
    type_unordered_scripts = []  # scripts to execute without order
    for _type_statement in _type_statements:
        _type_statement_parsed = sqlparse.parse(_type_statement)
        if len(_type_statement_parsed) > 0:  # can be empty parsed object so need to check
            # we need only type declarations to be ordered
            if _type_statement_parsed[0].get_type() == 'CREATE':
                _type_body_r = r'\bcreate\s+\btype\s+\b(\w+\.\w+|\w+)\b'
                _type_name = re.compile(_type_body_r, flags=re.IGNORECASE).findall(_type_statement)[0]
                _type_statements_dict[str(_type_name)] = \
                    {'script': _type_statement, 'deps': []}
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
    return type_ordered_scripts, type_unordered_scripts


def install_manager(connection_string):
    """
    Installs package manager
    """
    # Connect to DB
    print(TermStyle.PREFIX_INFO + 'Connecting to databases for deployment...')
    try:
        conn = psycopg2.connect(connection_string)
        cur = conn.cursor()
    except psycopg2.Error as e:
        print(TermStyle.PREFIX_ERROR + 'Connection to DB failed. Traceback: \n{0}'.format(e))
        exit(1)
    print(TermStyle.PREFIX_INFO + 'Connected to {0}'.format(connection_string))

    # Create schema if it doesn't exist
    cur.execute("SELECT EXISTS (SELECT schema_name FROM information_schema.schemata WHERE schema_name = '{0}');"
                .format(_variables.PGPM_SCHEMA_NAME))
    schema_exists = cur.fetchone()[0]
    if schema_exists:
        print(TermStyle.PREFIX_ERROR +
              'Can\'t install pgpm as schema {0} already exists'.format(_variables.PGPM_SCHEMA_NAME))
        close_db_conn(cur, conn, connection_string)
        exit()
    else:
        _install_script = pkgutil.get_data('pgpm', 'scripts/install.sql')
        print(TermStyle.PREFIX_INFO + 'Installing package manager')
        cur.execute(_install_script)

    # Commit transaction
    conn.commit()

    close_db_conn(cur, conn, connection_string)


def main():
    arguments = docopt(__doc__, version=_version.__version__)
    user_roles = arguments['--user']
    if arguments['--owner']:
        owner_role = arguments['--owner'][0]
    else:
        owner_role = ''
    files_deployment = arguments['--file']  # if specific script to be deployed, only find them
    if arguments['install']:
        install_manager(arguments['<connection_string>'])
    elif arguments['deploy']:
        # Load project configuration file
        print('\n' + TermStyle.PREFIX_INFO + 'Loading project configuration...')
        config_json = open('config.json')
        config_data = json.load(config_json)
        config_json.close()
        if arguments['--add-config']:
            print('\n' + TermStyle.PREFIX_INFO + 'Adding additional configuration file {0}'.
                  format(arguments['--add-config']))
            add_config_json = open(arguments['--add-config'])
            config_data = dict(config_data.items() + json.load(add_config_json).items())
            add_config_json.close()

        # Check if owner role and user roles are to be defined with config files
        if not owner_role and config_data['owner_role']:
            owner_role = config_data['owner_role']
        if not user_roles and config_data['user_roles']:
            user_roles = config_data['user_roles']

        print(TermStyle.PREFIX_INFO + 'Configuration of project {0} of version {1} loaded successfully.'
              .format(config_data['name'], config_data['version']))

        # Get scripts
        types_script, types_files_count = get_scripts("types_path", config_data, files_deployment, "types")
        functions_script, functions_files_count = get_scripts("functions_path", config_data, files_deployment,
                                                              "functions")
        views_script, views_files_count = get_scripts("views_path", config_data, files_deployment, "views")
        tables_script, tables_files_count = get_scripts("tables_path", config_data, files_deployment, "tables")
        triggers_script, triggers_files_count = get_scripts("triggers_path", config_data, files_deployment, "triggers")

        # Connect to DB
        print(TermStyle.PREFIX_INFO + 'Connecting to databases for deployment...')
        try:
            conn = psycopg2.connect(arguments['<connection_string>'])
            cur = conn.cursor()
        except psycopg2.Error as e:
            print(TermStyle.PREFIX_ERROR + 'Connection to DB failed. Traceback: \n{0}'.format(e))
            exit(1)
        print(TermStyle.PREFIX_INFO + 'Connected to {0}'.format(arguments['<connection_string>']))

        # Prepare and execute preamble
        _deployment_script_preamble = pkgutil.get_data('pgpm', 'scripts/deploy_prepare_config.sql')
        print(TermStyle.PREFIX_INFO + 'Executing a preamble to deployment statement')
        # print(_deployment_script_preamble)
        cur.execute(_deployment_script_preamble)

        # Get schema name from project configuration
        schema_name = ''
        if config_data['subclass'] == 'versioned':
            schema_name = '{0}_{1}'.format(config_data['name'], config_data['version'])
            print(TermStyle.PREFIX_INFO + 'Schema {0} will be updated'.format(schema_name))
        elif config_data['subclass'] == 'basic':
            schema_name = '{0}'.format(config_data['name'])
            if not arguments['--file']:
                print(TermStyle.PREFIX_INFO + 'Schema {0} will be created/replaced'.format(schema_name))
            else:
                print(TermStyle.PREFIX_INFO + 'Schema {0} will be updated'.format(schema_name))

        # Create schema or update it if exists (if not in production mode) and set search path
        cur.execute("SELECT EXISTS (SELECT schema_name FROM information_schema.schemata WHERE schema_name = '{0}');"
                    .format(schema_name))
        schema_exists = cur.fetchone()[0]
        if arguments['--file']:  # if specific scripts to be deployed
            if not schema_exists:
                print(TermStyle.PREFIX_ERROR + 'Can\'t deploy scripts to schema {0}. Schema doesn\'t exist in database'
                      .format(schema_name))
                close_db_conn(cur, conn, arguments.get('<connection_string>'))
                exit()
            else:
                _set_search_path_schema_script = "SET search_path TO {0}, public;".format(schema_name)
                cur.execute(_set_search_path_schema_script)
                print(TermStyle.PREFIX_INFO +
                      'Search_path was changed to schema {0}'
                      .format(schema_name))
        else:
            if not schema_exists:
                create_db_schema(cur, schema_name, ", ".join(user_roles), owner_role)
            elif arguments['--mode'][0] == 'safe':
                print(TermStyle.PREFIX_ERROR +
                      'Schema already exists. It won\'t be overriden in safe mode. Rerun your script without '
                      '"-m moderate" or "-m unsafe" flags')
                close_db_conn(cur, conn, arguments.get('<connection_string>'))
                exit()
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
                print(TermStyle.PREFIX_INFO +
                      'Schema already exists. It will be renamed to {0} in moderate mode. Renaming...'
                      .format(_old_schema_name))
                _rename_schema_script = "ALTER SCHEMA {0} RENAME TO {1};\n".format(schema_name, _old_schema_name)
                cur.execute(_rename_schema_script)
                print(TermStyle.PREFIX_INFO + 'Schema {0} was renamed to {1}.'.format(schema_name, _old_schema_name))
                create_db_schema(cur, schema_name, user_roles, owner_role)
            else:
                _drop_schema_script = "DROP SCHEMA {0} CASCADE;\n".format(schema_name)
                cur.execute(_drop_schema_script)
                print(TermStyle.PREFIX_INFO + 'Dropping old schema {0}'.format(schema_name))
                create_db_schema(cur, schema_name, user_roles, owner_role)

        # Reordering and executing types
        if types_files_count > 0:
            if arguments['--file']:
                print(TermStyle.PREFIX_WARNING +
                      'Deploying types definition scripts in existing schema without dropping it first '
                      'is not support yet. Skipping')
            else:
                type_ordered_scripts, type_unordered_scripts = reorder_types(types_script)
                # uncomment for debug
                # print(TermStyle.BOLD_ON + TermStyle.FONT_WHITE + '\n'.join(type_ordered_scripts))
                if type_ordered_scripts:
                    cur.execute('\n'.join(type_ordered_scripts))
                if type_unordered_scripts:
                    cur.execute('\n'.join(type_unordered_scripts))
                print(TermStyle.PREFIX_INFO + 'Types loaded to schema {0}'.format(schema_name))
        else:
            print(TermStyle.PREFIX_INFO + 'No type scripts to deploy')

        # Executing functions
        if functions_files_count > 0:
            print(TermStyle.PREFIX_INFO + 'Running functions definitions scripts')
            # print(TermStyle.HEADER + functions_script)
            cur.execute(functions_script)
            print(TermStyle.PREFIX_INFO + 'Functions loaded to schema {0}'.format(schema_name))
        else:
            print(TermStyle.PREFIX_INFO + 'No function scripts to deploy')

        # Executing views
        if views_files_count > 0:
            print(TermStyle.PREFIX_INFO + 'Running views definitions scripts')
            # print(TermStyle.HEADER + views_script)
            cur.execute(views_script)
            print(TermStyle.PREFIX_INFO + 'Views loaded to schema {0}'.format(schema_name))
        else:
            print(TermStyle.PREFIX_INFO + 'No view scripts to deploy')

        # Executing tables
        if tables_files_count > 0:
            print(TermStyle.PREFIX_WARNING + 'Support for DDL or data updates is not implemented yet')
        else:
            print(TermStyle.PREFIX_INFO + 'No DDL or data update scripts to deploy')

        # Executing triggers
        if triggers_files_count > 0:
            print(TermStyle.PREFIX_INFO + 'Running views definitions scripts')
            # print(TermStyle.HEADER + triggers_script)
            cur.execute(triggers_script)
            print(TermStyle.PREFIX_INFO + 'Views loaded to schema {0}'.format(schema_name))
        else:
            print(TermStyle.PREFIX_INFO + 'No view scripts to deploy')

        # Commit transaction
        conn.commit()

        close_db_conn(cur, conn, arguments.get('<connection_string>'))

    else:
        print(arguments)

if __name__ == '__main__':
    main()
