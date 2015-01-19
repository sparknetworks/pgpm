#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Deployment script that will deploy Postgres schemas to a given DB
Copyright (c) Affinitas GmbH
 
Usage:
  dpm.py deploy [-p | --production] <connection_string>...
  dpm.py -h | --help
  dpm.py --version
Options:
  -h --help     Show this screen.
  --version     Show version.
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

        # Get schema name from project configuration
        if config_data['subclass'] == 'versioned':
            schema_name = '{0}_{1}'.format(config_data['name'], config_data['version'])
            print('Schema {0} will be updated'.format(schema_name))
        elif config_data['subclass'] == 'non-versioned':
            schema_name = '{0}'.format(config_data['name'])
            print('Schema {0} will be updated'.format(schema_name))
            
        # Create schema or update it if exists (if not in production mode) and set search path
        print(cur.execute("SELECT EXISTS (SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s);", (schema_name,)))
        if not cur.execute("SELECT EXISTS (SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s);", (schema_name,)):
            _create_schema_script = "\nCREATE SCHEMA " + schema_name + " ;\n"
            _create_schema_script += "\nGRANT USAGE ON SCHEMA " + schema_name + " TO public;\n"
            _create_schema_script += "\nSET search_path TO " + schema_name + ", public;\n"
            cur.execute(_create_schema_script)
            print('Schema {0} didn\'t exist. It was created and search_path was changed', (schema_name))
        elif arguments['-p']:
            print('Schema already exists. It won\'t be overriden in production mode. Rerun your script without -p or --production flag')
            close_db_conn(cur, conn, arguments.get('<connection_string>')[0])
            exit()
        else:
            _create_schema_script += "\nGRANT USAGE ON SCHEMA " + schema_name + " TO public;\n"
            _create_schema_script += "\nSET search_path TO " + schema_name + ", public;\n"
            cur.execute(_create_schema_script)
            print('Schema {0} and search_path was updated', (schema_name))
        
        # Commit transaction
        conn.commit()
        
        close_db_conn(cur, conn, arguments.get('<connection_string>')[0])
        
    else:
        print(arguments)
