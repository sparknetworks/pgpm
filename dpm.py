#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Deployment script that will deploy Postgres schemas to a given DB
Copyright (c) Affinitas GmbH
 
Usage:
  dpm.py deploy [-p | --production] <connection_string>... [-f | --file <list_of_files>...]
  dpm.py -h | --help
  dpm.py -v | --version
Options:
  -h --help                         Show this screen.
  -v --version                      Show version.
  -p --production                   Add constraints to deployment. Will not deploy versioned schema if it already exists in the DB
  -f <list_of_files>..., --file <list_of_files>...      Use it if you want to deploy only specific files (functions, types, etc). In that case these files if exist will be overriden. Should be followed by the list of names of files to deploy.

"""

__all__ = ['dpm']
__version__ = '0.0.1'


import os
import psycopg2
import json
import sqlparse
from pprint import pprint
from urllib.parse import urlparse
from docopt import docopt

def close_db_conn(cur, conn, conn_string):
    """
    Close DB connection and cursor
    """
    print('\nClosing connection to {0}...'.format(conn_string))
    cur.close()
    conn.close()
    print('Connection to {0} closed.'.format(conn_string))
    
def create_db_schema(cur, schema_name):
    """
    Create Postgres schema script and execute it on cursor
    """
    _create_schema_script = "\nCREATE SCHEMA " + schema_name + " ;\n"
    _create_schema_script += "GRANT USAGE ON SCHEMA " + schema_name + " TO public;\n"
    _create_schema_script += "SET search_path TO " + schema_name + ", public;"
    cur.execute(_create_schema_script)
    print('Schema {0} was created and search_path was changed. The following script was executed: {1}'.format(schema_name, _create_schema_script))
    
    
if __name__ == '__main__':
    arguments = docopt(__doc__, version=__version__)
    if arguments['deploy']:
        # Load project configuration file
        print('Loading project configuration...')
        config_json = open('config.json')
        config_data = json.load(config_json)
        print('Configuration of project {0} of version {1} loaded successfully.'.format(config_data['name'], config_data['version']))
        config_json.close()
        
        # Get types files and calculate order of execution
        if config_data['types_path']:
            types_path = config_data['types_path']
        else:
            types_path = "types"
        
        print('Getting scripts with types definitions')
        types_files_count = 0
        types_script = ''
        for subdir, dirs, files in os.walk(types_path):
            for file in files:
                if arguments['--file']: # if specific script to be deployed, only find them
                    for list_file_name in arguments['--file']:
                        if file == list_file_name:
                            types_files_count += 1
                            types_script += open(os.path.join(subdir, file), 'r', -1, 'UTF-8').read()
                            types_script += '\n'
                            print('{0}\n'.format(os.path.join(subdir, file)))
                else: # if the whole schema to be deployed
                    types_files_count += 1
                    types_script += open(os.path.join(subdir, file), 'r', -1, 'UTF-8').read()
                    types_script += '\n'
                    print('{0}\n'.format(os.path.join(subdir, file)))
        if types_files_count == 0:
            print('No types definitions were found in {0} folder'.format(types_path))
        
        # Get functions scripts
        if config_data['functions_path']:
            functions_path = config_data['functions_path']
        else:
            functions_path = "functions"

        print('Getting scripts with functions definitions')
        functions_files_count = 0
        functions_script = ''
        for subdir, dirs, files in os.walk(functions_path):
            for file in files:
                if arguments['--file']: # if specific script to be deployed, only find them
                    for list_file_name in arguments['--file']:
#                        print('{0} -- {1}'.format(file, list_file_name))
#                        print('{0}'.format(arguments['--file']))
                        if file == list_file_name:
                            functions_files_count += 1
                            functions_script += open(os.path.join(subdir, file), 'r', -1, 'UTF-8').read()
                            functions_script += '\n'
                            print('{0}\n'.format(os.path.join(subdir, file)))
                else: # if the whole schema to be deployed       
                    functions_files_count += 1
                    functions_script += open(os.path.join(subdir, file), 'r', -1, 'UTF-8').read()
                    functions_script += '\n'
                    print('{0}\n'.format(os.path.join(subdir, file)))
        if functions_files_count == 0:
            print('No functions definitions were found in {0} folder'.format(functions_path))

        
        # Connect to DB
        print('\nConnecting to databases for deployment...')
        pg_conn_str_parsed = urlparse(arguments.get('<connection_string>')[0])
        pg_conn_username = pg_conn_str_parsed.username
        pg_conn_password = pg_conn_str_parsed.password
        pg_conn_database = pg_conn_str_parsed.path[1:]
        pg_conn_hostname = pg_conn_str_parsed.hostname
        try:
            conn = psycopg2.connect(arguments['<connection_string>'][0])
            cur = conn.cursor()
        except psycopg2.Error as e:
            exit('Connection to DB failed ', e)
        print('Connected to ', arguments['<connection_string>'][0])

        # Prepare and execute preamble
        _deploymeny_script_preamble = "--\n"            \
            "-- Start of composed deployment script\n"  \
            "-- \n"                                     \
            "SET statement_timeout = 0;\n"              \
            "SET client_encoding = 'UTF8';\n"           \
            "SET standard_conforming_strings = off;\n"  \
            "SET check_function_bodies = false;\n"      \
            "SET client_min_messages = warning;\n"      \
            "SET escape_string_warning = off;\n"
        print('Executing a preamble to deployment statement')
        print(_deploymeny_script_preamble)
        cur.execute(_deploymeny_script_preamble)

        # Get schema name from project configuration
        schema_name = ''
        if config_data['subclass'] == 'versioned':
            schema_name = '{0}_{1}'.format(config_data['name'], config_data['version'])
            print('Schema {0} will be updated'.format(schema_name))
        elif config_data['subclass'] == 'non-versioned':
            schema_name = '{0}'.format(config_data['name'])
            print('Schema {0} will be created/replaced'.format(schema_name))
            
        # Create schema or update it if exists (if not in production mode) and set search path
        cur.execute("SELECT EXISTS (SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s);", (schema_name,))
        schema_exists = cur.fetchone()[0]
        if arguments['--file']: # if specific scripts to be deployed
            if not schema_exists:
                print('Can\'t deploy scripts to schema {0}. Schema doesn\'t exist in database'.format(schema_name))
                close_db_conn(cur, conn, arguments.get('<connection_string>')[0])
                exit()
        else:
            if not schema_exists:
                create_db_schema(cur, schema_name)
            elif arguments['--production'] == 1:
                print('Schema already exists. It won\'t be overriden in production mode. Rerun your script without -p or --production flag')
                close_db_conn(cur, conn, arguments.get('<connection_string>')[0])
                exit()
            else:
                _drop_schema_script = "\nDROP SCHEMA " + schema_name + " CASCADE;\n"
                cur.execute(_drop_schema_script)
                print('Droping old schema {0}'.format(schema_name))
                create_db_schema(cur, schema_name)
        
        # Executing functions and types now
        if types_files_count > 0:
            if arguments['--file']:
                print('Deploying types definition scripts in existing schema without droping it first is not support yet. Skipping')
            else:
                print('Running types definitions scripts')
    #            print(sqlparse.split(types_script))
    #            print('\n')
    #            print(sqlparse.parse(types_script))
    #            print('\n')
    #            print(sqlparse.parse(types_script)[0].tokens)
    #            print('\n')
    #            print(str(sqlparse.parse(types_script)[0].tokens[-2]))
                cur.execute(types_script)
                print('Types loaded to schema {0}'.format(schema_name))
        else:
            print('No type scripts to deploy')

        if functions_files_count > 0:
            print('Running functions definitions scripts')
            cur.execute(functions_script)
            print('Functions loaded to schema {0}'.format(schema_name))
        else:
            print('No function scripts to deploy')
        
        # Commit transaction
        conn.commit()
        
        close_db_conn(cur, conn, arguments.get('<connection_string>')[0])
        
    else:
        print(arguments)
