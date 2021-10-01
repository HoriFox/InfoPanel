import pymysql

class DBConnection:
    log = None
    connect = None

    def __init__(self, log, **kwargs):
        self.log = log
        try:
            self.connect = pymysql.connect(**kwargs)
        except pymysql.err.OperationalError as err:
            self.log.error('OperationalError local except: %s' % err)
        except pymysql.Error as err:
            self.log.error('Error local except: %s' % err)

    def __del__(self):
        if self.connect:
            self.connect.close()

    def insert(self, table, is_replace = False, timestamp = None, **kwargs):
        if self.connect == None:
            self.log.warning('Connect not exist!')
            return

        query = ''
        
        try:
            cursor = self.connect.cursor()
            placeholders = ', '.join(['%s'] * len(kwargs))
            columns = ', '.join(kwargs.keys())
            query = "INSERT INTO %s (%s) VALUES (%s)" % (table, columns, placeholders)
            if is_replace:
                placeholders_update = ', '.join('`{}`=VALUES(`{}`)'.format(key, key)
                                                 for key in list(kwargs.keys())[1:])
                if timestamp:
                    placeholders_update += ', `' + timestamp + '`=NOW()'
                query += " ON DUPLICATE KEY UPDATE %s" % (placeholders_update)
            cursor.execute(query, list(kwargs.values()))
        except pymysql.Error as err:
            self.log.error('Error local except: %s' % err)
        else:
            self.connect.commit()

        return query

    def select(self, table, where = None, json = False):
        if self.connect == None:
            self.log.warning('Connect not exist!')
            return

        result = ''

        try:
            cursor = self.connect.cursor()
            query = "SELECT * FROM %s" % (table)
            if where:
                query += " WHERE %s" % (where)
            cursor.execute(query)
            result = cursor.fetchall()
            if json:
                result = [dict((cursor.description[i][0], value) for i, value in enumerate(row)) for row in result]
        except pymysql.Error as err:
            self.log.error('Error local except: %s' % err)

        return result

    def delete(self, table, where):
        if self.connect == None:
            self.log.warning('Connect not exist!')
            return

        try:
            cursor = self.connect.cursor()
            query = "DELETE FROM %s WHERE %s" % (table, where)
            cursor.execute(query)
        except pymysql.Error as err:
            self.log.error('Error local except: %s' % err)
        else:
            self.connect.commit()
