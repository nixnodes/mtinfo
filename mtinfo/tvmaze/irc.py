from ..irc import BaseCommandProcessor
from .tvmaze import SearchContext, LookupContext, SEARCH_MODE_SINGLE, ResultMulti, stamptodt
from .helpers import GenericShowHelper
from ..logging import Logger

from ..istor_schema import update as schema_update

import json, time, calendar, datetime
import pydle

logger = Logger(__name__)

from tornado import gen, concurrent

schema_update({
    'irc_watchlist': [
        { 'k' : 'id', 't': 'integer', 'f': 'index'},
        { 'k' : 'last_sent', 't': 'real', 'f': 'number', 'd': 0},
        { 'k' : 'user', 't': 'text', 'f': 'text'},
        { 'k' : 'host', 't': 'text', 'f': 'text'},
        { 'k' : 'data', 't': 'text', 'f': 'text'},
    ],
})

executor = concurrent.futures.ThreadPoolExecutor(8)


class TVMazeIRCCP(BaseCommandProcessor):

    FORMAT_SHOW = '{name} / {rating}'

    WATCH_REMINDER_INTERVAL = 3600

    def __init__(self, cache = None):
        self.cache = cache
        self.__last_wr_check = time.monotonic()
        self.__wrsched_handle = None

    @pydle.coroutine
    def get_show_by_id(self, tvmazeid):
        return LookupContext(
            mode = 'tvmaze',
            embed = [
                'nextepisode',
                'previousepisode'
            ],
            helper = GenericShowHelper,
            cache = self.cache
        ).query(str(tvmazeid))

    @pydle.coroutine
    def get_show_by_name(self, q):
        return SearchContext(
            mode = SEARCH_MODE_SINGLE,
            embed = [
                'nextepisode',
                'previousepisode'
            ],
            helper = GenericShowHelper,
            cache = self.cache
        ).query(q)

    @pydle.coroutine
    def get_show(self, client, source, *args):
        if not args or not args[0]:
            return

        f = args[0]

        if len(args) > 1 and f[0] == '-':

            q = args[1]
            m = f[1]

            if m == 'i':
                return (yield executor.submit(self.get_show_by_id, q)).result()
            else:
                raise Exception('Unknown flag {} from {}'.format(m, source))

        else:
            return (yield executor.submit(self.get_show_by_name, ' '.join(args))).result()

    def cache_get_by_user(self, table, username, hostname):
        c = self.cache.conn.cursor()

        outstr = 'SELECT * FROM {} WHERE host = ? AND user = ?'.format(table)

        return c.execute (
            outstr,
            (hostname, username)
        )

    @pydle.coroutine
    def lookup_async(self, f, *args):
        try:
            result = (yield executor.submit(f, *args)).result()
            if result.is_cached:
                return result
        except BaseException as e:
            logger.exception(e)
            result = False

        yield gen.sleep(0.5)
        return result

    @pydle.coroutine
    def dispatch_watch_reminder(self, client, row, i = None):

        data = json.loads(row['data'])

        if len(data) == 0:
            return

        e = []

        wrcache = False

        for k, v in data.items():

            if i != None and k != i:
                continue

            result = yield self.lookup_async(self.get_show_by_id, v['id'])

            if not result or not result.nextepisode:
                continue

            deltat = calendar.timegm(stamptodt(result.data._embedded.nextepisode.airstamp).utctimetuple()) - time.time()

            if deltat < 0 or deltat > 43200:
                continue

            if 'last_sent' in v and time.time() - v['last_sent'] < 86400:
                continue

            v['last_sent'] = time.time()
            wrcache = True

            e.append((result, deltat))

            if i != None:
                break

        if e:
            user = yield client.find_user(row['user'], row['host'])
            if not user:
                return
            nick = user['nickname']

            client.message(nick, ':: Watch reminder ::')
            for v in e:
                result = v[0]
                deltat = v[1]
                client.message(nick, ':: {} :: {} (in {} hrs)'.format(result.name, result.nextepisode, round(deltat / 3600, 1)))

            row['data'] = json.dumps(data, ensure_ascii = False)
            wrcache = True

        if wrcache:
            self.cache.set('irc_watchlist', row)
            self.cache.commit()

    @pydle.coroutine
    def dispatch_wr_global(self, client):
        for row in self.cache.getall('irc_watchlist'):
            if not (yield client.find_user(row['user'], row['host'])):
                continue

            yield self.dispatch_watch_reminder(client, row)

    @pydle.coroutine
    def watchlist_add(self, client, source, nick, *args):

        if not args:
            return

        user = client.users[nick]

        username = user['username']
        hostname = user['hostname']

        result = (yield self.get_show(client, source , *args))

        row = self.cache_get_by_user('irc_watchlist', username, hostname).fetchone()

        if not row:
            row = {
                'user': username,
                'host': hostname
            }
            data = {}
        else:
            data = json.loads(row['data'])

        data[str(result.data.id)] = {
            'id': result.data.id,
            'name': result.name,
        }

        row['data'] = json.dumps(data, ensure_ascii = False)

        self.cache.set('irc_watchlist', row)
        self.cache.commit()

        client.message(source, 'Added \'{}\' to watchlist'.format(result.name))

        yield self.dispatch_watch_reminder(client, row, i = str(result.data.id))

    @pydle.coroutine
    def watchlist_remove(self, client, source, nick, *args):
        if not args:
            return

        user = client.users[nick]

        result = (yield self.get_show(client, source , *args))

        row = self.cache_get_by_user('irc_watchlist', user['username'], user['hostname']).fetchone()

        if not row:
            return

        data = json.loads(row['data'])

        _id = str(result.data.id)

        if not _id in data:
            return

        del data[_id]

        row['data'] = json.dumps(data, ensure_ascii = False)

        self.cache.set('irc_watchlist', row)
        self.cache.commit()

        client.message(source, 'Removed \'{}\' from watchlist'.format(result.name))

    def convert_timedelta(self, duration):
        seconds = duration.seconds
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        seconds = (seconds % 60)
        return hours, minutes, seconds

    def fmt_time(self, seconds):
        td = datetime.timedelta(seconds = seconds)
        hours, minutes, seconds = self.convert_timedelta(td)

        o = ''
        if td.days > 0:
            o += '{}d '.format(td.days)

        if hours > 0:
            o += '{}h '.format(hours)

        o += '{}m'.format(minutes)
        return o

    @pydle.coroutine
    def watchlist_list(self, client, source, nick):
        user = client.users[nick]

        row = self.cache_get_by_user('irc_watchlist', user['username'], user['hostname']).fetchone()

        if not row:
            return

        data = json.loads(row['data'])

        for v in data.values():

            result = yield self.lookup_async(self.get_show_by_id, v['id'])

            if not result:
                continue

            o = ':: {}'.format(result.name)

            if result.nextepisode:
                deltat = calendar.timegm(stamptodt(result.data._embedded.nextepisode.airstamp).utctimetuple()) - time.time()
                o += ' | Next: {} (in {})'.format(result.nextepisode, self.fmt_time(deltat))

            client.message(source, o)

    @pydle.coroutine
    def schedule_wr_users(self, client, nick):
        for v in client.users.values():
            if nick != v['nickname']:
                row = self.cache_get_by_user('irc_watchlist', v['username'], v['hostname']).fetchone()
                if row:
                    yield self.dispatch_watch_reminder(client, row)

        self.__wrsched_handle = None

    @pydle.coroutine
    def on_tick(self, client):
        t = time.monotonic()
        if t - self.__last_wr_check >= self.WATCH_REMINDER_INTERVAL:
            self.__last_wr_check = t
            yield self.dispatch_wr_global(client)

    @pydle.coroutine
    def on_join(self, client, channel, nick):
        if nick == client.nickname:
            if self.__wrsched_handle:
                client.eventloop.unschedule(self.__wrsched_handle)
                self.__wrsched_handle = None

            self.__wrsched_handle = client.eventloop.schedule_in(15, self.schedule_wr_users, client, nick)

        else:
            user = client.users[nick]
            row = self.cache_get_by_user('irc_watchlist', user['username'], user['hostname']).fetchone()
            if row:
                self.dispatch_watch_reminder(client, row)

    @pydle.coroutine
    def cmd_tv(self, client, source, user, *args):

        result = yield self.get_show(client, source, *args)

        fmt = client.options.get('show_format')
        if not fmt:
            fmt = self.FORMAT_SHOW

        if isinstance(result, ResultMulti):
            for v in result:
                client.message(source, v.format(fmt))
        else:
            client.message(source, result.format(fmt))

    @pydle.coroutine
    def cmd_watch(self, client, source , nick, *args):

        if not args or not args[0]:
            self.watchlist_list(client, source, nick)
        else:
            c = args[0]

            if c == 'add':
                yield self.watchlist_add(client, source, nick, *args[1:])
            elif c == 'remove':
                yield self.watchlist_remove(client, source, nick, *args[1:])
            elif c == 'list':
                yield self.watchlist_list(client, source, nick)

