
import time
import pydle

from .data import DStorBase
from .logging import Logger

logger = Logger(__name__)

from pydle import connection


class Client(pydle.Client):

    RECONNECT_MAX_ATTEMPTS = None
    MT_DELIMITERS = '.'
    PING_INTERVAL = 90

    def __init__(self, *args, options = None, **kwargs):

        if options != None:
            assert isinstance(options, dict)

        super(Client, self).__init__(*args, **kwargs)

        self.options = DStorBase(options)

        self.__mt_cpa = []

        self.__reconnect_handler = None
        self.__pinger_handle = None
        self.__tick_handler = None

    def register_command_processor(self, cp):
        assert issubclass(cp.__class__, BaseCommandProcessor)

        for v in self.__mt_cpa:
            if v.__class__ == cp.__class__:
                raise Exception('Command processor already registered')

        self.__mt_cpa.append(cp)

    def unregister_command_processor(self, cp):
        self.__mt_cpa.remove(cp)

    def on_connect(self):
        super().on_connect()
        self._reconnect_attempts = 0
        if self.PING_INTERVAL > 0:
            self.__do_ping()
        self.__tick_handler = self.eventloop.schedule_periodically(1, self.__do_tick)
        self.__run_cpa('on_connect')

    def on_join(self, channel, user):
        super().on_join(channel, user)
        self.__run_cpa('on_join', channel, user)

    @pydle.coroutine
    def __do_tick(self):
        for v in self.__mt_cpa:
            try:
                v.on_tick(self)
            except BaseException as e:
                logger.exception(e)

    @pydle.coroutine
    def __run_cpa(self, f, *args, **kwargs):
        for v in self.__mt_cpa:
            try:
                getattr(v, f)(self, *args, **kwargs)
            except BaseException as e:
                logger.exception(e)

    def __do_ping(self):
        if self.connected:
            self.rawmsg('PING', str(int(time.time())))
            self.__pinger_handle = self.eventloop.schedule_in(self.PING_INTERVAL, self.__do_ping)

    @pydle.coroutine
    def find_user_match(self, v, username, hostname):
        return (v['username'] == username and
                v['hostname'] == hostname)

    @pydle.coroutine
    def find_user(self, username, hostname):
        for v in self.users.values():
            if (yield self.find_user_match(v, username, hostname)):
                return v

    @pydle.coroutine
    def on_message(self, source, target, message):
        # self.message(target, message)

        if not self.__mt_cpa:
            return

        if self.is_channel(source):
            if not self.in_channel(source):
                return

        elif self.is_same_nick(source, self.nickname):
            source = target

        if len(message) < 2:
            return

        if not message[0] in self.MT_DELIMITERS:
            return

        c = message.split(' ')
        q = c.pop(0)[1:]

        for v in self.__mt_cpa:
            if (yield v.run(self, q, c, source, target)):
                break

    def on_raw_pong(self, source):
        pass

    def on_kick(self, channel, target, by, reason = None):
        if self.options.get('rejoin_on_kick', False):
            if self.is_same_nick(target, self.nickname):
                self.eventloop.schedule_in(5, lambda: self.join(channel) if self.connected else None)

    def on_disconnect(self, expected):
        if self.__pinger_handle != None:
            self.eventloop.unschedule(self.__pinger_handle)
            self.__pinger_handle = None

        if self.__tick_handler != None:
            self.eventloop.unschedule(self.__tick_handler)
            self.__tick_handler = None

        if self.__reconnect_handler == None:
            if not expected:
                # Unexpected disconnect. Reconnect?
                if self.RECONNECT_ON_ERROR and (self.RECONNECT_MAX_ATTEMPTS is None or self._reconnect_attempts < self.RECONNECT_MAX_ATTEMPTS):
                    # Calculate reconnect delay.
                    delay = 5
                    self._reconnect_attempts += 1

                    if delay > 0:
                        self.logger.error('Unexpected disconnect. Attempting to reconnect within %s seconds.', delay)
                    else:
                        self.logger.error('Unexpected disconnect. Attempting to reconnect.')

                    def do_reconnect(self):
                        self.__reconnect_handler = None
                        if not self.connected:
                            self.connect(reconnect = True)

                    # Wait and reconnect.
                    self.__reconnect_handler = self.eventloop.schedule_in(delay, do_reconnect, self)
                else:
                    self.logger.error('Unexpected disconnect. Giving up.')


class BaseCommandProcessor():

    @pydle.coroutine
    def run(self, client, q, c, source, target):
        f = getattr(self, 'cmd_' + q, None)
        if f == None or not callable(f):
            return False

        try:
            yield f(client, source, target, *c)
        except BaseException as e:
            logger.exception('Exception while executing command: {}'.format(e))

        return True

    @pydle.coroutine
    def on_tick(self, client):
        pass

    @pydle.coroutine
    def on_join(self, client, channel, user):
        pass

    @pydle.coroutine
    def on_connect(self, client):
        pass


def run_client(parser, config, cache = None, cpcs = None):

    assert cpcs and isinstance(cpcs, list)

    throttle_threshold = config.get('irc', 'throttle_threshold', fallback = None)
    if throttle_threshold != None:
        connection.MESSAGE_THROTTLE_TRESHOLD = int(throttle_threshold)

    throttle_delay = config.get('irc', 'throttle_delay', fallback = None)
    if throttle_delay != None:
        connection.MESSAGE_THROTTLE_DELAY = int(throttle_delay)

    server = config.get('irc', 'server')

    port = int(config.get('irc', 'port', fallback = 6667))
    tls = bool(config.get('irc', 'tls', fallback = False))
    tls_verify = bool(config.get('irc', 'tls_verify', fallback = False))

    channels = config.get('irc', 'channels')
    channels = channels.split(',')

    client = Client(
        config.get('irc', 'nick', fallback = 'mtbot'),
        realname = 'mtbot',
        username = 'mtbot',
        options = dict(config.items('irc'))
    )

    for v in cpcs:
        client.register_command_processor(v)

    client.connect(
        server,
        port,
        tls = tls,
        tls_verify = tls_verify,
        channels = channels
    )

    try:
        client.handle_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        try:
            client.disconnect()
        except BaseException as e:
            logger.exception(e)

    logger.debug('IRC client shutting down')
