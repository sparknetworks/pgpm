import psycopg2
import psycopg2.extensions
import logging

# class

class ConnectionManager:
    """
    Simple DB connections manager. Acts as a pool with one connection
    """

    def __init__(self, connection_string, logger=None):
        """
        Initializes connection to DB
        """
        conn = psycopg2.connect(connection_string)
        self._connection_string = connection_string
        self._conn = conn
        self.logger = logger or logging.getLogger(__name__)

    def get_connection_db(self):
        """
        Connect to DB or exit on exception
        """
        if not self._conn or self._conn.closed != 0:
            conn = psycopg2.connect(self._connection_string)
            self._conn = conn
            return conn
        else:
            return self._conn

    def close_connection_db(self):
        """
        Close DB connection and cursor
        """
        if not self._conn:
            return None
        else:
            return self._conn.close()

    def call_stored_procedure_safely(self, name, arguments_list=None, commit=True):
        """
        Calls pg stored procedure and returns cursor.
        Wrapper also rollbacks on exception and logs activity
        :param name: name of procedure
        :param arguments_list: arguments
        :return: cursor
        """
        conn = self.get_connection_db()
        cur = conn.cursor()
        try:
            if arguments_list:
                cur.callproc(name, arguments_list)
                self.logger.debug('Stored procedure {0} with arguments {1} called'.format(name, arguments_list))
            else:
                cur.callproc(name)
                self.logger.debug('Stored procedure {0} called'.format(name))
            if commit:
                conn.commit()
        except psycopg2.InternalError:
            conn.close()
            conn = self.get_connection_db()
            self.logger.exception('Database error')
            pass
        except:
            conn.rollback()
            self.logger.exception('Database error')
            pass

        return cur



