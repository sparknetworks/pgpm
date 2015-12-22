import logging
import pkgutil
import distutils.version
import sys

import pkg_resources
import psycopg2
import re

import pgpm.lib.utils
import pgpm.lib.utils.db
import pgpm.lib.version
import pgpm.lib.utils.config


class InstallationManager:
    """
    Class that will manage pgpm installation
    """
    def __init__(self, connection_string, pgpm_schema_name='_pgpm', pgpm_schema_subclass='basic', logger=None):
        """
        initialises the manager and connects to the DB
        :param connection_string: connection string consumable by DBAPI 2.0
        :param logger: logger object
        """
        self._main_module_name = 'pgpm'

        self._connection_string = connection_string
        self._conn = psycopg2.connect(connection_string, connection_factory=pgpm.lib.utils.db.MegaConnection)
        self._pgpm_schema_name = pgpm_schema_name
        self._pgpm_schema_subclass = pgpm_schema_subclass
        self._pgpm_version = pgpm.lib.utils.config.Version(pgpm.lib.version.__version__,
                                                           pgpm.lib.utils.config.VersionTypes.python)
        self._logger = logger or logging.getLogger(__name__)
        self._conn.init(logger)

    def install_pgpm_to_db(self, user_roles, upgrade=False):
        """
        Installs package manager

        """
        if self._conn.closed:
            self._conn = psycopg2.connect(self._connection_string, connection_factory=pgpm.lib.utils.db.MegaConnection)

        cur = self._conn.cursor()

        # get pgpm functions
        scripts_dict = pgpm.lib.utils.collect_scripts_from_sources('lib/db_scripts/functions', False, '.', True,
                                                                   self._logger)

        # get current user
        cur.execute(pgpm.lib.utils.db.SqlScriptsHelper.current_user_sql)
        current_user = cur.fetchone()[0]

        # check if current user is a super user
        cur.execute(pgpm.lib.utils.db.SqlScriptsHelper.is_superuser_sql)
        is_cur_superuser = cur.fetchone()[0]
        if not is_cur_superuser:
            self._logger.debug('User {0} is not a superuser. It is recommended that you connect as superuser '
                               'when installing pgpm as some operation might need superuser rights'
                               .format(current_user))

        # Create schema if it doesn't exist
        if pgpm.lib.utils.db.SqlScriptsHelper.schema_exists(cur, self._pgpm_schema_name):
            # Executing pgpm functions
            if len(scripts_dict) > 0:
                self._logger.info('Running functions definitions scripts')
                self._logger.debug(scripts_dict)
                pgpm.lib.utils.db.SqlScriptsHelper.set_search_path(cur, self._pgpm_schema_name)
                for key, value in scripts_dict.items():
                    if value:
                        cur.execute(value)
                self._logger.debug('Functions loaded to schema {0}'.format(self._pgpm_schema_name))
            else:
                self._logger.debug('No function scripts to deploy')

            self._conn.commit()

            # check installed version of _pgpm schema.
            pgpm_v_db_tuple = pgpm.lib.utils.db.SqlScriptsHelper.get_pgpm_db_version(cur, self._pgpm_schema_name)
            pgpm_v_db = distutils.version.StrictVersion(".".join(pgpm_v_db_tuple))
            pgpm_v_script = distutils.version.StrictVersion(pgpm.lib.version.__version__)
            if pgpm_v_script > pgpm_v_db:
                if upgrade:
                    self._migrate_pgpm_version(cur, pgpm_v_db, pgpm_v_script, True)
                else:
                    self._migrate_pgpm_version(cur, pgpm_v_db, pgpm_v_script, False)
            elif pgpm_v_script < pgpm_v_db:
                self._logger.error('Deployment script\'s version is lower than the version of {0} schema '
                                   'installed in DB. Update pgpm script first.'.format(self._pgpm_schema_name))
                self._close_db_conn(cur)
                sys.exit(1)
            else:
                self._logger.error('Can\'t install pgpm as schema {0} already exists'.format(self._pgpm_schema_name))
                self._close_db_conn(cur)
                sys.exit(1)
        else:
            # Prepare and execute preamble
            deployment_script_preamble = pkgutil.get_data(self._main_module_name, 'lib/db_scripts/deploy_prepare_config.sql')
            self._logger.info('Executing a preamble to install statement')
            cur.execute(deployment_script_preamble)

            # Python 3.x doesn't have format for byte strings so we have to convert
            install_script = pkgutil.get_data(self._main_module_name, 'lib/db_scripts/install.tmpl.sql').decode('utf-8')
            self._logger.info('Installing package manager')
            cur.execute(install_script.format(schema_name=self._pgpm_schema_name))
            migration_files_list = sorted(pkg_resources.resource_listdir(self._main_module_name, 'lib/db_scripts/migrations/'),
                                          key=lambda filename: distutils.version.StrictVersion(filename.split('-')[0]))
            # Executing pgpm functions
            if len(scripts_dict) > 0:
                self._logger.info('Running functions definitions scripts')
                self._logger.debug(scripts_dict)
                pgpm.lib.utils.db.SqlScriptsHelper.set_search_path(cur, self._pgpm_schema_name)
                for key, value in scripts_dict.items():
                    cur.execute(value)
                self._logger.debug('Functions loaded to schema {0}'.format(self._pgpm_schema_name))
            else:
                self._logger.debug('No function scripts to deploy')

            # Executing migration scripts after as they contain triggers that trigger functions that were created on top
            for file_info in migration_files_list:
                # Python 3.x doesn't have format for byte strings so we have to convert
                migration_script = pkg_resources.resource_string(self._main_module_name, 'lib/db_scripts/migrations/{0}'.format(file_info))\
                    .decode('utf-8').format(schema_name=self._pgpm_schema_name)
                self._logger.debug('Running version upgrade script {0}'.format(file_info))
                self._logger.debug(migration_script)
                cur.execute(migration_script)

            cur.callproc('_add_migration_info', ['0.0.7', pgpm.lib.version.__version__])
            self._conn.commit()

        # check if users of pgpm are specified
        if not user_roles:
            self._logger.debug('No user was specified to have permisions on _pgpm schema. '
                               'This means only user that installed _pgpm will be able to deploy. '
                               'We recommend adding more users.')
        else:
            # set default privilages to users
            pgpm.lib.utils.db.SqlScriptsHelper.grant_default_usage_install_privileges(
                cur, self._pgpm_schema_name, ', '.join(user_roles))
            pgpm.lib.utils.db.SqlScriptsHelper.grant_usage_install_privileges(
                cur, self._pgpm_schema_name, ', '.join(user_roles))

        pgpm.lib.utils.db.SqlScriptsHelper.set_search_path(cur, self._pgpm_schema_name)
        cur.callproc('_upsert_package_info',
                     [self._pgpm_schema_name, self._pgpm_schema_subclass,
                      self._pgpm_version.major, self._pgpm_version.minor, self._pgpm_version.patch,
                      self._pgpm_version.pre, self._pgpm_version.metadata,
                      'Package manager for Postgres', 'MIT'])
        # Commit transaction
        self._conn.commit()

        self._close_db_conn(cur)

        return 0

    def uninstall_pgpm_from_db(self):
        """
        Removes pgpm from db and all related metadata (_pgpm schema). Install packages are left as they are
        :return: 0 if successful and error otherwise
        """
        drop_schema_cascade_script = 'DROP SCHEMA {schema_name} CASCADE;'

        if self._conn.closed:
            self._conn = psycopg2.connect(self._connection_string, connection_factory=pgpm.lib.utils.db.MegaConnection)

        cur = self._conn.cursor()

        # get current user
        cur.execute(pgpm.lib.utils.db.SqlScriptsHelper.current_user_sql)
        current_user = cur.fetchone()[0]

        # check if current user is a super user
        cur.execute(pgpm.lib.utils.db.SqlScriptsHelper.is_superuser_sql)
        is_cur_superuser = cur.fetchone()[0]
        if not is_cur_superuser:
            self._logger.debug('User {0} is not a superuser. Only superuser can remove pgpm'
                               .format(current_user))
            sys.exit(1)

        self._logger.debug('Removing pgpm from DB by dropping schema {0}'.format(self._pgpm_schema_name))
        cur.execute(drop_schema_cascade_script.format(schema_name=self._pgpm_schema_name))

        # Commit transaction
        self._conn.commit()

        self._close_db_conn(cur)

        return 0

    def _migrate_pgpm_version(self, cur, version_pgpm_db, version_pgpm_script,  migrate_or_leave):
        """
        Enact migration script from one version of pgpm to another (newer)
        :param cur:
        :param migrate_or_leave: True if migrating, False if exiting
        :return:
        """
        migrations_file_re = r'^(.*)-(.*).tmpl.sql$'
        migration_files_list = sorted(pkg_resources.resource_listdir(self._main_module_name, 'lib/db_scripts/migrations/'),
                                      key=lambda filename: distutils.version.StrictVersion(filename.split('-')[0]))
        for file_info in migration_files_list:
            versions_list = re.compile(migrations_file_re, flags=re.IGNORECASE).findall(file_info)
            version_a = distutils.version.StrictVersion(versions_list[0][0])
            version_b = distutils.version.StrictVersion(versions_list[0][1])
            if version_pgpm_script >= version_a and version_b > version_pgpm_db:
                # Python 3.x doesn't have format for byte strings so we have to convert
                migration_script = pkg_resources.resource_string(self._main_module_name, 'lib/db_scripts/migrations/{0}'.format(file_info))\
                    .decode('utf-8').format(schema_name=self._pgpm_schema_name)
                if migrate_or_leave:
                    self._logger.debug('Running version upgrade script {0}'.format(file_info))
                    self._logger.debug(migration_script)
                    cur.execute(migration_script)
                    self._conn.commit()
                    pgpm.lib.utils.db.SqlScriptsHelper.set_search_path(cur, self._pgpm_schema_name)
                    cur.callproc('_add_migration_info', [versions_list[0][0], versions_list[0][1]])
                    self._conn.commit()
                    self._logger.debug('Successfully finished running version upgrade script {0}'.format(file_info))

        if not migrate_or_leave:
            self._logger.error('{0} schema version is outdated. Please run pgpm install --upgrade first.'
                               .format(self._pgpm_schema_name))
            self._close_db_conn(cur)
            sys.exit(1)

    def _close_db_conn(self, cur):
        """
        Close DB connection and cursor
        """
        self._logger.debug('Closing connection to {0}...'.format(self._conn.dsn))
        cur.close()
        self._conn.close()
        self._logger.debug('Connection to {0} closed.'.format(self._conn.dsn))
