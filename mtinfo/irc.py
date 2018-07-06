
import time
import pydle

from .data import DStorBase
from .logging import Logger

logger = Logger(__name__)


class MTBot(pydle.Client):

    RECONNECT_MAX_ATTEMPTS = None
    MT_DELIMITERS = '.'
    PING_INTERVAL = 90

    def __init__(self, *args, options = None, cp = None, **kwargs):

        if options != None:
            assert isinstance(options, dict)

        if cp != None:
            assert issubclass(cp.__class__, BaseCommandProcessor)

        super(MTBot, self).__init__(*args, **kwargs)

        if hasattr(self, 'options'):
            raise Exception('C-C-C')

        self.options = DStorBase(options)

        self._mt_cp = cp

        self._reconnect_handler = None
        self._pinger_handle = None

    def on_connect(self):
        super().on_connect()
        self._reconnect_attempts = 0
        self._do_ping()

    def _do_ping(self):
        if self.connected:
            self.rawmsg('PING', str(int(time.time())))
            self._pinger_handle = self.eventloop.schedule_in(self.PING_INTERVAL, self._do_ping)

    def on_message(self, source, target, message):
        # self.message(target, message)

        if not self._mt_cp:
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

        self._mt_cp.run(self, q, c, source, target)

    def on_raw_pong(self, source):
        pass

    def on_kick(self, channel, target, by, reason = None):
        if self.options.get('rejoin_on_kick', False):
            if self.is_same_nick(target, self.nickname):
                self.eventloop.schedule_in(5, lambda: self.join(channel) if self.connected else None)

    def on_disconnect(self, expected):
        if self._pinger_handle != None:
            self.eventloop.unschedule(self._pinger_handle)
            self._pinger_handle = None

        if not self._reconnect_handler:
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
                        self._reconnect_handler = None
                        if not self.connected:
                            self.connect(reconnect = True)

                    # Wait and reconnect.
                    self._reconnect_handler = self.eventloop.schedule_in(delay, do_reconnect, self)
                else:
                    self.logger.error('Unexpected disconnect. Giving up.')


class BaseCommandProcessor():

    def run(self, client, q, c, source, target):
        f = getattr(self, 'cmd_' + q, None)
        if f == None or not callable(f):
            return

        try:
            f(client, source, target, *c)
        except BaseException as e:
            logger.exception('Exception while executing command: {}'.format(e))

