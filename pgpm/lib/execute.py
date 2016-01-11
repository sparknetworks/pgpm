import logging
import distutils.version
import sys

import psycopg2
import sqlparse
import csv

import pgpm.lib.utils
import pgpm.lib.utils.db
import pgpm.lib.version
import pgpm.lib.utils.config
import pgpm.lib.utils.vcs


class QueryExecutionManager:
    """
    Class that will manage calling procedures
    """
    def __init__(self, connection_string, pgpm_schema_name='_pgpm', logger=None):
        """
        initialises the manager and connects to the DB
        :param connection_string: connection string consumable by DBAPI 2.0
        :param logger: logger object
        """
        self._logger = logger or logging.getLogger(__name__)
        self._connection_string = connection_string
        self._conn = psycopg2.connect(connection_string, connection_factory=pgpm.lib.utils.db.MegaConnection)
        self._conn.init(logger)
        self._pgpm_schema_name = pgpm_schema_name
        self._logger.debug('Initialised db connection.')
        self._pgpm_version = pgpm.lib.utils.config.Version(pgpm.lib.version.__version__,
                                                           pgpm.lib.utils.config.VersionTypes.python)

    def execute(self, query, until_zero=False):
        """
        Execute a query
        :param query: query to execute
        :param until_zero: should query be called until returns 0
        :return:
        """

        if self._conn.closed:
            self._conn = psycopg2.connect(self._connection_string, connection_factory=pgpm.lib.utils.db.MegaConnection)
        cur = self._conn.cursor()

        # be cautious, dangerous thing
        self._conn.autocommit = True

        # Check if DB is pgpm enabled
        if not pgpm.lib.utils.db.SqlScriptsHelper.schema_exists(cur, self._pgpm_schema_name):
            self._logger.error('Can\'t deploy schemas to DB where pgpm was not installed. '
                               'First install pgpm by running pgpm install')
            self._close_db_conn(cur)
            sys.exit(1)

        # check installed version of _pgpm schema.
        pgpm_v_db_tuple = pgpm.lib.utils.db.SqlScriptsHelper.get_pgpm_db_version(cur, self._pgpm_schema_name)
        pgpm_v_db = distutils.version.StrictVersion(".".join(pgpm_v_db_tuple))
        pgpm_v_script = distutils.version.StrictVersion(pgpm.lib.version.__version__)
        if pgpm_v_script > pgpm_v_db:
            self._logger.error('{0} schema version is outdated. Please run pgpm install --upgrade first.'
                               .format(self._pgpm_schema_name))
            self._close_db_conn(cur)
            sys.exit(1)
        elif pgpm_v_script < pgpm_v_db:
            self._logger.error('Deployment script\'s version is lower than the version of {0} schema '
                               'installed in DB. Update pgpm script first.'.format(self._pgpm_schema_name))
            self._close_db_conn(cur)
            sys.exit(1)


        # Executing query
        if until_zero:
            self._logger.debug('Running query {0} until it returns 0 (but not more than 10000 times'
                               .format(query))
            proc_return_value = None
            counter = 0
            while proc_return_value != 0:
                cur.execute(query)
                proc_return_value = cur.fetchone()[0]
                counter += 1
                if counter > 9999:
                    break
        else:
            self._logger.debug('Running query {0}'.format(query))
            cur.execute(query)

        # Commit transaction
        self._conn.commit()

        self._close_db_conn(cur)

        return 0

    def _close_db_conn(self, cur):
        """
        Close DB connection and cursor
        """
        self._logger.debug('Closing connection to {0}...'.format(self._conn.dsn))
        cur.close()
        self._conn.close()
        self._logger.debug('Connection to {0} closed.'.format(self._conn.dsn))
