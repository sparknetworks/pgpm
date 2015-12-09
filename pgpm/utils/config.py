import json
import re
import os

import pgpm.lib.utils.db
import psycopg2
import psycopg2.extras


class GlobalConfiguration(object):
    """
    stores properties of schema configuration
    """
    description = ""
    license = ""
    owner_role = ""
    user_roles = []

    def __init__(self, default_config_path='~/.pgpmconfig', extra_config_path=None):
        """
        populates properties with config data
        """

        global_config_dict = None
        default_config = None
        extra_config = None
        if default_config_path:
            default_config_full_path = os.path.abspath(os.path.expanduser(default_config_path))
            if os.path.isfile(default_config_full_path):
                default_config_file = open(default_config_full_path)
                default_config = json.load(default_config_file)
                default_config_file.close()
        if extra_config_path:
            extra_config_full_path = os.path.abspath(os.path.expanduser(extra_config_path))
            if os.path.isfile(extra_config_full_path):
                extra_config_file = open(extra_config_full_path)
                extra_config = json.load(extra_config_file)
                extra_config_file.close()
        if default_config and extra_config:
            global_config_dict = dict(list(default_config) + list(extra_config.items()))
        elif default_config:
            global_config_dict = default_config
        elif extra_config:
            global_config_dict = extra_config

        self.global_config_dict = global_config_dict

        self.connection_sets = []
        if self.global_config_dict:
            if 'connection_sets' in self.global_config_dict:
                for item in self.global_config_dict['connection_sets']:
                    if item['type'] == 'RESDB':
                        conn = psycopg2.connect(item['connection_string'], connection_factory=pgpm.lib.utils.db.MegaConnection)
                        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                        cur.execute(item['payload'])
                        result_tuple = cur.fetchall()
                        self.connection_sets = self.connection_sets + result_tuple
                        cur.close()
                        conn.close()
                    if item['type'] == 'LIST':
                        self.connection_sets = self.connection_sets + item['payload']

    def get_list_connections(self, environment, product):
        return_list = []
        for item in self.connection_sets:
            if item['environment'] == environment and item['product'] == product:
                return_list.append(item)

        return return_list