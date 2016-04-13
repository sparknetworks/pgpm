import json
import logging
import pkgutil
import distutils.version
import sys
import collections

import os
import psycopg2
import re
import sqlparse

import pgpm.lib.abstract_deploy
import pgpm.lib.utils
import pgpm.lib.utils.db
import pgpm.lib.utils.misc
import pgpm.lib.version
import pgpm.lib.utils.config
import pgpm.lib.utils.vcs


class DeploymentManager(pgpm.lib.abstract_deploy.AbstractDeploymentManager):
    """
    Class that will manage db code deployments
    """
    def __init__(self, connection_string, source_code_path=None, config_path=None, config_dict=None, config_object=None,
                 pgpm_schema_name='_pgpm', logger=None):
        """
        initialises the manager and connects to the DB
        :param connection_string: connection string consumable by DBAPI 2.0
        :param source_code_path: path to where package is
        :param config_path: string or array to where config/configs are
        :param config_dict: dictionary with config
        :param config_object: SchemaConfiguration object
        :param logger: logger object
        """

        super(DeploymentManager, self).__init__(connection_string, pgpm_schema_name, logger)
        if source_code_path:
            self._source_code_path = source_code_path
        elif config_path:
            self._source_code_path = os.path.dirname(config_path)

        if config_object:
            self._config = config_object
        else:
            self._config = pgpm.lib.utils.config.SchemaConfiguration(config_path, config_dict, self._source_code_path)
        self._logger.debug('Loading project configuration...')

    def deploy_schema_to_db(self, mode='safe', files_deployment=None, vcs_ref=None, vcs_link=None,
                            issue_ref=None, issue_link=None, compare_table_scripts_as_int=False,
                            config_path=None, config_dict=None, config_object=None, source_code_path=None,
                            auto_commit=False):
        """
        Deploys schema
        :param files_deployment: if specific script to be deployed, only find them
        :param mode:
        :param vcs_ref:
        :param vcs_link:
        :param issue_ref:
        :param issue_link:
        :param compare_table_scripts_as_int:
        :param config_path:
        :param config_dict:
        :param config_object:
        :param source_code_path:
        :param auto_commit:
        :return: dictionary of the following format:
            {
                code: 0 if all fine, otherwise something else,
                message: message on the output
                function_scripts_requested: list of function files requested for deployment
                function_scripts_deployed: list of function files deployed
                type_scripts_requested: list of type files requested for deployment
                type_scripts_deployed: list of type files deployed
                view_scripts_requested: list of view files requested for deployment
                view_scripts_deployed: list of view files deployed
                trigger_scripts_requested: list of trigger files requested for deployment
                trigger_scripts_deployed: list of trigger files deployed
                table_scripts_requested: list of table files requested for deployment
                table_scripts_deployed: list of table files deployed
                requested_files_count: count of requested files to deploy
                deployed_files_count: count of deployed files
            }
        :rtype: dict
        """

        return_value = {}
        if files_deployment:
            return_value['function_scripts_requested'] = files_deployment
            return_value['type_scripts_requested'] = []
            return_value['view_scripts_requested'] = []
            return_value['trigger_scripts_requested'] = []
            return_value['table_scripts_requested'] = []

        if auto_commit:
            if mode == 'safe' and files_deployment:
                self._logger.debug("Auto commit mode is on. Be careful.")
            else:
                self._logger.error("Auto commit deployment can only be done with file "
                                   "deployments and in safe mode for security reasons")
                raise ValueError("Auto commit deployment can only be done with file "
                                 "deployments and in safe mode for security reasons")

        # set source code path if exists
        self._source_code_path = self._source_code_path or source_code_path

        # set configuration if either of config_path, config_dict, config_object are set.
        # Otherwise use configuration from class initialisation
        if config_object:
            self._config = config_object
        elif config_path or config_dict:
            self._config = pgpm.lib.utils.config.SchemaConfiguration(config_path, config_dict, self._source_code_path)

        # Check if in git repo
        if not vcs_ref:
            if pgpm.lib.utils.vcs.is_git_directory(self._source_code_path):
                vcs_ref = pgpm.lib.utils.vcs.get_git_revision_hash(self._source_code_path)
                self._logger.debug('commit reference to be deployed is {0}'.format(vcs_ref))
            else:
                self._logger.debug('Folder is not a known vcs repository')

        self._logger.debug('Configuration of package {0} of version {1} loaded successfully.'
                           .format(self._config.name, self._config.version.raw))  # TODO: change to to_string once discussed
        # .format(self._config.name, self._config.version.to_string()))

        # Get scripts
        type_scripts_dict = self._get_scripts(self._config.types_path, files_deployment,
                                              "types", self._source_code_path)
        if not files_deployment:
            return_value['type_scripts_requested'] = [key for key in type_scripts_dict]

        function_scripts_dict = self._get_scripts(self._config.functions_path, files_deployment,
                                                  "functions", self._source_code_path)
        if not files_deployment:
            return_value['function_scripts_requested'] = [key for key in function_scripts_dict]

        view_scripts_dict = self._get_scripts(self._config.views_path, files_deployment,
                                              "views", self._source_code_path)
        if not files_deployment:
            return_value['view_scripts_requested'] = [key for key in view_scripts_dict]

        trigger_scripts_dict = self._get_scripts(self._config.triggers_path, files_deployment,
                                                 "triggers", self._source_code_path)
        if not files_deployment:
            return_value['trigger_scripts_requested'] = [key for key in trigger_scripts_dict]

        # before with table scripts only file name was an identifier. Now whole relative path the file
        # (relative to config.json)
        # table_scripts_dict_denormalised = self._get_scripts(self._config.tables_path, files_deployment,
        #                                                     "tables", self._source_code_path)
        # table_scripts_dict = {os.path.split(k)[1]: v for k, v in table_scripts_dict_denormalised.items()}
        table_scripts_dict = self._get_scripts(self._config.tables_path, files_deployment,
                                               "tables", self._source_code_path)
        if not files_deployment:
            return_value['table_scripts_requested'] = [key for key in table_scripts_dict]

        if self._conn.closed:
            self._conn = psycopg2.connect(self._connection_string, connection_factory=pgpm.lib.utils.db.MegaConnection)
        cur = self._conn.cursor()

        # be cautious, dangerous thing
        if auto_commit:
            self._conn.autocommit = True

        # Check if DB is pgpm enabled
        if not pgpm.lib.utils.db.SqlScriptsHelper.schema_exists(cur, self._pgpm_schema_name):
            self._logger.error('Can\'t deploy schemas to DB where pgpm was not installed. '
                               'First install pgpm by running pgpm install')
            self._conn.close()
            sys.exit(1)

        # check installed version of _pgpm schema.
        pgpm_v_db_tuple = pgpm.lib.utils.db.SqlScriptsHelper.get_pgpm_db_version(cur, self._pgpm_schema_name)
        pgpm_v_db = distutils.version.StrictVersion(".".join(pgpm_v_db_tuple))
        pgpm_v_script = distutils.version.StrictVersion(pgpm.lib.version.__version__)
        if pgpm_v_script > pgpm_v_db:
            self._logger.error('{0} schema version is outdated. Please run pgpm install --upgrade first.'
                               .format(self._pgpm_schema_name))
            self._conn.close()
            sys.exit(1)
        elif pgpm_v_script < pgpm_v_db:
            self._logger.error('Deployment script\'s version is lower than the version of {0} schema '
                               'installed in DB. Update pgpm script first.'.format(self._pgpm_schema_name))
            self._conn.close()
            sys.exit(1)

        # Resolve dependencies
        list_of_deps_ids = []
        if self._config.dependencies:
            _is_deps_resolved, list_of_deps_ids, _list_of_unresolved_deps = \
                self._resolve_dependencies(cur, self._config.dependencies)
            if not _is_deps_resolved:
                self._logger.error('There are unresolved dependencies. Deploy the following package(s) and try again:')
                for unresolved_pkg in _list_of_unresolved_deps:
                    self._logger.error('{0}'.format(unresolved_pkg))
                self._conn.close()
                sys.exit(1)

        # Prepare and execute preamble
        _deployment_script_preamble = pkgutil.get_data('pgpm', 'lib/db_scripts/deploy_prepare_config.sql')
        self._logger.debug('Executing a preamble to deployment statement')
        cur.execute(_deployment_script_preamble)

        # Get schema name from project configuration
        schema_name = ''
        if self._config.scope == pgpm.lib.utils.config.SchemaConfiguration.SCHEMA_SCOPE:
            if self._config.subclass == 'versioned':
                schema_name = '{0}_{1}'.format(self._config.name, self._config.version.raw)

                self._logger.debug('Schema {0} will be updated'.format(schema_name))
            elif self._config.subclass == 'basic':
                schema_name = '{0}'.format(self._config.name)
                if not files_deployment:
                    self._logger.debug('Schema {0} will be created/replaced'.format(schema_name))
                else:
                    self._logger.debug('Schema {0} will be updated'.format(schema_name))

        # Create schema or update it if exists (if not in production mode) and set search path
        if files_deployment:  # if specific scripts to be deployed
            if self._config.scope == pgpm.lib.utils.config.SchemaConfiguration.SCHEMA_SCOPE:
                if not pgpm.lib.utils.db.SqlScriptsHelper.schema_exists(cur, schema_name):
                    self._logger.error('Can\'t deploy scripts to schema {0}. Schema doesn\'t exist in database'
                                       .format(schema_name))
                    self._conn.close()
                    sys.exit(1)
                else:
                    pgpm.lib.utils.db.SqlScriptsHelper.set_search_path(cur, schema_name)
                    self._logger.debug('Search_path was changed to schema {0}'.format(schema_name))
        else:
            if self._config.scope == pgpm.lib.utils.config.SchemaConfiguration.SCHEMA_SCOPE:
                if not pgpm.lib.utils.db.SqlScriptsHelper.schema_exists(cur, schema_name):
                    pgpm.lib.utils.db.SqlScriptsHelper.create_db_schema(cur, schema_name)
                elif mode == 'safe':
                    self._logger.error('Schema already exists. It won\'t be overriden in safe mode. '
                                       'Rerun your script with "-m moderate", "-m overwrite" or "-m unsafe" flags')
                    self._conn.close()
                    sys.exit(1)
                elif mode == 'moderate':
                    old_schema_exists = True
                    old_schema_rev = 0
                    while old_schema_exists:
                        old_schema_exists = pgpm.lib.utils.db.SqlScriptsHelper.schema_exists(
                            cur, schema_name + '_' + str(old_schema_rev))
                        if old_schema_exists:
                            old_schema_rev += 1
                    old_schema_name = schema_name + '_' + str(old_schema_rev)
                    self._logger.debug('Schema already exists. It will be renamed to {0} in moderate mode. Renaming...'
                                       .format(old_schema_name))
                    _rename_schema_script = "ALTER SCHEMA {0} RENAME TO {1};\n".format(schema_name, old_schema_name)
                    cur.execute(_rename_schema_script)
                    # Add metadata to pgpm schema
                    pgpm.lib.utils.db.SqlScriptsHelper.set_search_path(cur, self._pgpm_schema_name)
                    cur.callproc('_set_revision_package'.format(self._pgpm_schema_name),
                                 [self._config.name,
                                  self._config.subclass,
                                  old_schema_rev,
                                  self._config.version.major,
                                  self._config.version.minor,
                                  self._config.version.patch,
                                  self._config.version.pre])
                    self._logger.debug('Schema {0} was renamed to {1}. Meta info was added to {2} schema'
                                       .format(schema_name, old_schema_name, self._pgpm_schema_name))
                    pgpm.lib.utils.db.SqlScriptsHelper.create_db_schema(cur, schema_name)
                elif mode == 'unsafe':
                    _drop_schema_script = "DROP SCHEMA {0} CASCADE;\n".format(schema_name)
                    cur.execute(_drop_schema_script)
                    self._logger.debug('Dropping old schema {0}'.format(schema_name))
                    pgpm.lib.utils.db.SqlScriptsHelper.create_db_schema(cur, schema_name)

        if self._config.scope == pgpm.lib.utils.config.SchemaConfiguration.SCHEMA_SCOPE:
            pgpm.lib.utils.db.SqlScriptsHelper.set_search_path(cur, schema_name)

        # Reordering and executing types
        return_value['type_scripts_deployed'] = []
        if len(type_scripts_dict) > 0:
            types_script = '\n'.join([''.join(value) for key, value in type_scripts_dict.items()])
            type_drop_scripts, type_ordered_scripts, type_unordered_scripts = self._reorder_types(types_script)
            if type_drop_scripts:
                for statement in type_drop_scripts:
                    if statement:
                        cur.execute(statement)
            if type_ordered_scripts:
                for statement in type_ordered_scripts:
                    if statement:
                        cur.execute(statement)
            if type_unordered_scripts:
                for statement in type_unordered_scripts:
                    if statement:
                        cur.execute(statement)
            self._logger.debug('Types loaded to schema {0}'.format(schema_name))
            return_value['type_scripts_deployed'] = [key for key in type_scripts_dict]
        else:
            self._logger.debug('No type scripts to deploy')

        # Executing Table DDL scripts
        executed_table_scripts = []
        return_value['table_scripts_deployed'] = []
        if len(table_scripts_dict) > 0:
            if compare_table_scripts_as_int:
                sorted_table_scripts_dict = collections.OrderedDict(sorted(table_scripts_dict.items(),
                                                                           key=lambda t: int(t[0].rsplit('.', 1)[0])))
            else:
                sorted_table_scripts_dict = collections.OrderedDict(sorted(table_scripts_dict.items(),
                                                                           key=lambda t: t[0].rsplit('.', 1)[0]))

            self._logger.debug('Running Table DDL scripts')
            for key, value in sorted_table_scripts_dict.items():
                pgpm.lib.utils.db.SqlScriptsHelper.set_search_path(cur, self._pgpm_schema_name)
                cur.callproc('_is_table_ddl_executed'.format(self._pgpm_schema_name), [
                    key,
                    self._config.name,
                    self._config.subclass,
                    self._config.version.major,
                    self._config.version.minor,
                    self._config.version.patch,
                    self._config.version.pre
                ])
                is_table_executed = cur.fetchone()[0]
                if self._config.scope == pgpm.lib.utils.config.SchemaConfiguration.SCHEMA_SCOPE:
                    pgpm.lib.utils.db.SqlScriptsHelper.set_search_path(cur, schema_name)
                elif self._config.scope == pgpm.lib.utils.config.SchemaConfiguration.DATABASE_SCOPE:
                    cur.execute("SET search_path TO DEFAULT ;")
                if (not is_table_executed) or (mode == 'unsafe'):
                    # if auto commit mode than every statement is called separately.
                    # this is done this way as auto commit is normally used when non transaction statements are called
                    # then this is needed to avoid "cannot be executed from a function or multi-command string" errors
                    if auto_commit:
                        for statement in sqlparse.split(value):
                            if statement:
                                cur.execute(statement)
                    else:
                        cur.execute(value)
                    self._logger.debug(value)
                    self._logger.debug('{0} executed for schema {1}'.format(key, schema_name))
                    executed_table_scripts.append(key)
                    return_value['table_scripts_deployed'].append(key)
                else:
                    self._logger.debug('{0} is not executed for schema {1} as it has already been executed before. '
                                       .format(key, schema_name))
        else:
            self._logger.debug('No Table DDL scripts to execute')

        # Executing functions
        return_value['function_scripts_deployed'] = []
        if len(function_scripts_dict) > 0:
            self._logger.debug('Running functions definitions scripts')
            for key, value in function_scripts_dict.items():
                # if auto commit mode than every statement is called separately.
                # this is done this way as auto commit is normally used when non transaction statements are called
                # then this is needed to avoid "cannot be executed from a function or multi-command string" errors
                if auto_commit:
                    for statement in sqlparse.split(value):
                        if statement:
                            cur.execute(statement)
                else:
                    cur.execute(value)
                return_value['function_scripts_deployed'].append(key)
            self._logger.debug('Functions loaded to schema {0}'.format(schema_name))
        else:
            self._logger.debug('No function scripts to deploy')

        # Executing views
        return_value['view_scripts_deployed'] = []
        if len(view_scripts_dict) > 0:
            self._logger.debug('Running views definitions scripts')
            for key, value in view_scripts_dict.items():
                # if auto commit mode than every statement is called separately.
                # this is done this way as auto commit is normally used when non transaction statements are called
                # then this is needed to avoid "cannot be executed from a function or multi-command string" errors
                if auto_commit:
                    for statement in sqlparse.split(value):
                        if statement:
                            cur.execute(statement)
                else:
                    cur.execute(value)
                return_value['view_scripts_deployed'].append(key)
            self._logger.debug('Views loaded to schema {0}'.format(schema_name))
        else:
            self._logger.debug('No view scripts to deploy')

        # Executing triggers
        return_value['trigger_scripts_deployed'] = []
        if len(trigger_scripts_dict) > 0:
            self._logger.debug('Running trigger definitions scripts')
            for key, value in trigger_scripts_dict.items():
                # if auto commit mode than every statement is called separately.
                # this is done this way as auto commit is normally used when non transaction statements are called
                # then this is needed to avoid "cannot be executed from a function or multi-command string" errors
                if auto_commit:
                    for statement in sqlparse.split(value):
                        if statement:
                            cur.execute(statement)
                else:
                    cur.execute(value)
                return_value['trigger_scripts_deployed'].append(key)
            self._logger.debug('Triggers loaded to schema {0}'.format(schema_name))
        else:
            self._logger.debug('No trigger scripts to deploy')

        # alter schema privileges if needed
        if (not files_deployment) and mode != 'overwrite' \
                and self._config.scope == pgpm.lib.utils.config.SchemaConfiguration.SCHEMA_SCOPE:
            pgpm.lib.utils.db.SqlScriptsHelper.revoke_all(cur, schema_name, 'public')
            if self._config.usage_roles:
                pgpm.lib.utils.db.SqlScriptsHelper.grant_usage_privileges(
                    cur, schema_name, ', '.join(self._config.usage_roles))
                self._logger.debug('User(s) {0} was (were) granted usage permissions on schema {1}.'
                                   .format(", ".join(self._config.usage_roles), schema_name))
            if self._config.owner_role:
                pgpm.lib.utils.db.SqlScriptsHelper.set_search_path(cur, self._pgpm_schema_name)
                cur.callproc('_alter_schema_owner', [schema_name, self._config.owner_role])
                self._logger.debug('Ownership of schema {0} and all its objects was changed and granted to user {1}.'
                                   .format(schema_name, self._config.owner_role))

        # Add metadata to pgpm schema
        pgpm.lib.utils.db.SqlScriptsHelper.set_search_path(cur, self._pgpm_schema_name)
        cur.callproc('_upsert_package_info'.format(self._pgpm_schema_name),
                     [self._config.name,
                      self._config.subclass,
                      self._config.version.major,
                      self._config.version.minor,
                      self._config.version.patch,
                      self._config.version.pre,
                      self._config.version.metadata,
                      self._config.description,
                      self._config.license,
                      list_of_deps_ids,
                      vcs_ref,
                      vcs_link,
                      issue_ref,
                      issue_link])
        self._logger.debug('Meta info about deployment was added to schema {0}'
                           .format(self._pgpm_schema_name))
        pgpm_package_id = cur.fetchone()[0]
        if len(table_scripts_dict) > 0:
            for key in executed_table_scripts:
                cur.callproc('_log_table_evolution'.format(self._pgpm_schema_name), [key, pgpm_package_id])

        # Commit transaction
        self._conn.commit()

        self._conn.close()

        deployed_files_count = len(return_value['function_scripts_deployed']) + \
                               len(return_value['type_scripts_deployed']) + \
                               len(return_value['view_scripts_deployed']) + \
                               len(return_value['trigger_scripts_deployed']) + \
                               len(return_value['table_scripts_deployed'])

        requested_files_count = len(return_value['function_scripts_requested']) + \
                                len(return_value['type_scripts_requested']) + \
                                len(return_value['view_scripts_requested']) + \
                                len(return_value['trigger_scripts_requested']) + \
                                len(return_value['table_scripts_requested'])

        return_value['deployed_files_count'] = deployed_files_count
        return_value['requested_files_count'] = requested_files_count
        if deployed_files_count == requested_files_count:
            return_value['code'] = self.DEPLOYMENT_OUTPUT_CODE_OK
            return_value['message'] = 'OK'
        else:
            return_value['code'] = self.DEPLOYMENT_OUTPUT_CODE_NOT_ALL_DEPLOYED
            return_value['message'] = 'Not all requested files were deployed'
        return return_value

    def _get_scripts(self, scripts_path_rel, files_deployment, script_type, project_path):
        """
        Gets scripts from specified folders
        """

        scripts_dict = {}
        if scripts_path_rel:

            self._logger.debug('Getting scripts with {0} definitions'.format(script_type))
            scripts_dict = pgpm.lib.utils.misc.collect_scripts_from_sources(scripts_path_rel, files_deployment,
                                                                            project_path, False, self._logger)
            if len(scripts_dict) == 0:
                self._logger.debug('No {0} definitions were found in {1} folder'.format(script_type, scripts_path_rel))
        else:
            self._logger.debug('No {0} folder was specified'.format(script_type))

        return scripts_dict

    def _resolve_dependencies(self, cur, dependencies):
        """
        Function checks if dependant packages are installed in DB
        """
        list_of_deps_ids = []
        _list_of_deps_unresolved = []
        _is_deps_resolved = True
        for k, v in dependencies.items():
            pgpm.lib.utils.db.SqlScriptsHelper.set_search_path(cur, self._pgpm_schema_name)
            cur.execute("SELECT _find_schema('{0}', '{1}')"
                        .format(k, v))
            pgpm_v_ext = tuple(cur.fetchone()[0][1:-1].split(','))
            try:
                list_of_deps_ids.append(int(pgpm_v_ext[0]))
            except:
                pass
            if not pgpm_v_ext[0]:
                _is_deps_resolved = False
                _list_of_deps_unresolved.append("{0}: {1}".format(k, v))

        return _is_deps_resolved, list_of_deps_ids, _list_of_deps_unresolved

    def _reorder_types(self, types_script):
        """
        Takes type scripts and reorders them to avoid Type doesn't exist exception
        """
        self._logger.debug('Running types definitions scripts')
        self._logger.debug('Reordering types definitions scripts to avoid "type does not exist" exceptions')
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
        # _type_statements_list = []  # list of statements to be ordered
        for _type_key in _type_statements_dict.keys():
            for _type_key_sub, _type_value in _type_statements_dict.items():
                if _type_key != _type_key_sub:
                    if pgpm.lib.utils.misc.find_whole_word(_type_key)(_type_value['script']):
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

