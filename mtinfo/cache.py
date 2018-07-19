import threading, json
import sqlite3

from .data import DStorBase

from .logging import (
    Logger
)

logger = Logger(__name__)


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class IStorException(Exception):
    pass


class IStor:

    def __init__(self, path, schema):

        self._path = path
        self.conn = conn = sqlite3.connect(self._path, check_same_thread = False)
        self._schema = schema

        self.data = DStorBase()

        c = conn.cursor()
        conn.row_factory = dict_factory

        for k, v in schema.items():
            s = ''
            for i, d in enumerate(v):
                if i > 0:
                    s += ','

                if 'd' in d:
                    defstr = ' DEFAULT {}'.format(d['d'])
                else:
                    defstr = ''

                s += '{} {} {} {}'.format(
                    d['k'],
                    d['t'],
                    'PRIMARY KEY' if d['f'] == 'index' else '',
                    defstr
                )

            c.execute('CREATE TABLE IF NOT EXISTS {} ({})'.format(k, s))

        for k, v in schema.items():
            t = c.execute('PRAGMA table_info({})'.format(k))

            _d = {}
            for r in t:
                _d[r[1]] = True

            for i, d in enumerate(v):
                if not d['k'] in _d:

                    if d['f'] == 'index':
                        raise IStorException('Cannot add index column to table')

                    if 'd' in d:
                        defstr = 'NOT NULL DEFAULT {}'.format(d['d'])
                    else:
                        defstr = ''

                    s = 'ALTER TABLE {} ADD COLUMN {} {} {}'.format(
                        k,
                        d['k'],
                        d['t'],
                        defstr
                    )

                    c.execute(s)

        self._lock = threading.RLock()

    def __enter__(self):
        self._lock.acquire()

    def __exit__(self, *a):
        self._lock.release()

    def close(self):
        with self._lock:
            self.conn.commit()
            self.conn.close()

    def commit(self):
        with self._lock:
            self.conn.commit()

    def get(self, table, k, v, sort = None, order = None):

        with self._lock:
            sitem = self.schema_find_item(table, k)
            if not sitem:
                return []

            t = sitem['t']

            if t == 'integer':
                f = 'SELECT * FROM {} WHERE {} = ?'
            elif t == 'text':
                f = 'SELECT * FROM {} WHERE {} LIKE ?'
                v = '%'.join(v.split(' ')) + '%'
            else:
                raise IStorException('Unknown type')

            if sort:
                f += ' ORDER BY {}'.format(sort)
                if order:
                    f += ' ' + order

            c = self.conn.cursor()

            outstr = f.format(
                table,
                k
            )

            return c.execute (
                outstr,
                (v,)
            ).fetchall()

    def getall(self, table, sort = None, order = None):
        with self._lock:
            f = "SELECT * FROM {}".format(table)
            if sort:
                f += ' ORDER BY {}'.format(sort)
                if order:
                    f += ' ' + order

            return self.conn.cursor().execute (f)

    def getone(self, *args):
        r = self.get(*args)
        for v in r:
            return v

    def set(self, table, data):

        with self._lock:
            schema = self._schema[table]

            r = data

            c = ''
            v = ''
            w = 0

            out = []

            for d in schema:

                k = d['k']

                if not k in r:
                    continue

                if w > 0:
                    c += ','
                    v += ','

                c += k

                if d['f'] == 'json':
                    out.append(json.dumps(r[k], ensure_ascii = False))
                else:
                    out.append(r[k])

                w += 1

                v += '?'

            if not out:
                return

            outstr = 'INSERT OR REPLACE INTO {} ({}) VALUES({})'.format(
                table, c, v
            )

            c = self.conn.cursor()
            c.execute (
                outstr,
                tuple(out)
            )

    def delete(self, table, key):
        with self._lock:
            index = self.schema_find_f(table, 'index')['k']

            conn = self.conn
            c = conn.cursor()

            outstr = 'DELETE FROM {} WHERE {} = ?'.format(
                table,
                index
            )

            return c.execute (
                outstr,
                tuple((key,))
            )

            # conn.commit()

    def schema_find_item(self, table, k):
        schema = self._schema[table]

        for i in schema:
            if i['k'] == k:
                return i

    def schema_find_f(self, table, f):
        schema = self._schema[table]

        for i in schema:
            if i['f'] == f:
                return i

