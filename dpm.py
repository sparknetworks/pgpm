#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Deployment script that will deploy Postgres schemas to a given DB
Copyright (c) Affinitas GmbH
 
Usage:
  dpm.py deploy [-p | --production] <connection_string>...
  dpm.py -h | --help
  dpm.py -v | --version
Options:
  -h --help     Show this screen.
  -v --version     Show version.
  -p --production   Add constraints to deployment. Will not deploy versioned schema if it already exists in the DB

"""

__all__ = ['dpm']
__version__ = '0.0.1'


import psycopg2
import json
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
        
        # Parse files to calculate order of execution
        # 1. Get types        
        
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
        if not cur.fetchone()[0]:
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
        
        # Commit transaction
        conn.commit()
        
        close_db_conn(cur, conn, arguments.get('<connection_string>')[0])
        
    else:
        print(arguments)
