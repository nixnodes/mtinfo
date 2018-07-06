import logging, argparse, json, time, sys

from ..logging import set_loglevel, Logger
from ..arg import _arg_parse_common
from ..cache import IStor
from .tests.generic import run as run_generic_test
from ..data import DStorBase

from ..irc import MTBot
from .irc import TVMazeIRCCP

from configparser import ConfigParser

CONFIG_FILE = '/etc/mtinfo.conf'

from .tvmaze import (
    SearchContext,
    LookupContext,
    ScheduleContext,
    PeopleContext,
    ResultMulti,
    Result,

    BaseNotFoundException,

    # RESULT_TYPE_NORMAL,
    RESULT_TYPE_LOOKUP,

    SEARCH_MODE_SINGLE,
    SEARCH_MODE_MULTI,

    ResultJSONEncoder,

    STORAGE_SCHEMA
)

from .helpers import (
    GenericShowHelper,
    GenericEpisodeHelper,
    print_informative
)

logger = Logger(__name__)


def _argparse(parser):
    parser.add_argument('-machine', action = 'store_true', help = 'Machine-readable output')
    parser.add_argument('-l', type = str, nargs = '?', help = 'Lookup by foreign ID [imdb|tvrage|thetvdb]')
    parser.add_argument('-i', action = 'store_true', help = 'Lookup by ID')
    parser.add_argument('-s', action = 'store_true', help = 'Today\'s schedule (US)')
    parser.add_argument('-p', action = 'store_true', help = 'Search people')
    parser.add_argument('-e', action = 'store_true', help = 'Embed episodes in query result')
    parser.add_argument('-m', action = 'store_true', help = 'Multiple results on search')
    parser.add_argument('-f', type = str, nargs = '?', help = 'Format output')
    parser.add_argument('-config', type = str, nargs = '?', help = 'Config file')
    parser.add_argument('-b', type = str, nargs = '?', help = 'Batch file')
    parser.add_argument('-list', action = 'store_true', help = 'List cache')
    parser.add_argument('-test', action = 'store_true', help = 'Run tests')
    parser.add_argument('-ircbot', action = 'store_true', help = '')
    parser.add_argument('-sort', type = str, nargs = '?', help = '')
    parser.add_argument('-order', type = str, nargs = '?', help = '')
    parser.add_argument('--cache', type = str, nargs = '?', help = 'Cache sqlite3 database')
    parser.add_argument('--cache_expire', type = int, nargs = '?', help = 'Cache expiration time')
    parser.add_argument('--rate_limit', type = str, nargs = '?', help = 'Query rate limit')
    parser.add_argument('query', nargs = '*')


def _do_print(r, machine = False, fmt = None):
    if fmt != None:
        if isinstance(r, ResultMulti):
            for v in r:
                print(v.format(fmt))
        else:
            print(r.format(fmt))
    elif machine:
        if isinstance(r, ResultMulti):
            o = []
            for v in r:
                o.append(v.data)
            print(ResultJSONEncoder().encode(o))
        else:
            print(ResultJSONEncoder().encode(r.data))
    else:
        if isinstance(r, ResultMulti):
            for v in r:
                print_informative(v)
        else:
            print_informative(r)


def do_query(context, q = None, machine = False, fmt = None, **kwargs):
    logger.debug("Query: '{}'".format(q))

    r = context(**kwargs).query(q)

    _do_print(r, machine, fmt)


def lookup_show(*args, a = None, embed = None, **kwargs):

    e = [
        'nextepisode',
        'previousepisode'
    ]

    if a.get('e'):
        e.extend(['episodes'])

    if a:
        fmt = a.get('f')
        machine = a.get('machine')

    do_query(
        *args,
        embed = e,
        fmt = fmt,
        machine = machine,
        helper = GenericShowHelper,
        **kwargs
    )


def do_list(cache = None, sort = None, order = None, **kwargs):
    for v in cache.getall('shows', sort = sort, order = order):
        result = Result(
            json.loads(v['data']),
            restype = RESULT_TYPE_LOOKUP,
            helper = GenericShowHelper,
        )
        _do_print(result, **kwargs)


def _do_search(qs, a, **kwargs):

    if a['i']:
        lookup_show(
            LookupContext,
            a = a,
            q = qs,
            mode = 'tvmaze',
            **kwargs
        )
    elif (a['l'] != None):
        lookup_show(
            LookupContext,
            q = qs,
            a = a,
            mode = a['l'],
            **kwargs
        )
    elif (a['p'] == True):
        do_query(
            PeopleContext,
            q = qs,
            fmt = a.get('f'),
            machine = a.get('machine'),
            **kwargs
        )
    else:
        lookup_show(
            SearchContext,
            mode = SEARCH_MODE_MULTI if a['m'] else SEARCH_MODE_SINGLE,
            a = a,
            q = qs,
            **kwargs
        )


def _invoke_search(qs, a, **kwargs):

    if a['b'] != None:
        if a['rate_limit'] != None:
            rate_limit = float(a['rate_limit'])
        else:
            rate_limit = 2

        sr = 0

        class rlst():

            def __init__(self, rate_limit):
                self._last_rlcheck = time.monotonic()
                self._rlcounter = 0
                self.rate_limit = rate_limit

        _rlst = rlst(rate_limit)

        def rlcallback(rlst):
            while rlst._rlcounter / (time.monotonic() - rlst._last_rlcheck) > rlst.rate_limit:
                time.sleep(0.03)

            rlst._rlcounter += 1

        def procline(l):
            l = l.rstrip()
            if len(l) == 0:
                return 0

            try:
                _do_search(l, a, rlcallback = lambda: rlcallback(_rlst), **kwargs)
            except BaseNotFoundException as e:
                logger.error(e)

            return 1

        if a['b'] == '-':
            for line in sys.stdin:
                sr += procline(line)
        else:
            with open(a['b'], 'r') as f:
                for line in f:
                    sr += procline(line)
    else:

        if (len(qs) == 0):
            raise Exception("Missing query")

        _do_search(qs, a, **kwargs)


def _run_irc_client(args, config, cache = None):

    server = config.get('irc', 'server')

    port = int(config.get('irc', 'port', fallback = 6667))
    tls = bool(config.get('irc', 'tls', fallback = False))
    tls_verify = bool(config.get('irc', 'tls_verify', fallback = False))

    channels = config.get('irc', 'channels')
    channels = channels.split(',')

    client = MTBot(
        config.get('irc', 'nick', fallback = 'mtbot'),
        realname = 'mtbot',
        username = 'mtbot',
        cp = TVMazeIRCCP(cache),
        options = dict(config.items('irc'))
    )
    client.connect(
        server,
        port,
        tls = tls,
        tls_verify = tls_verify,
        channels = channels
    )

    client.handle_forever()


def _main(a, config, cache = None, **kwargs):

    if a['ircbot']:
        return _run_irc_client(a, config, cache)

    embed = []

    if a['e']:
        embed.append('episodes')

    if a['list']:
        do_list(
            cache = cache,
            sort = a['sort'],
            order = a['order'],
            machine = a['machine'],
            fmt = a['f']
        )
    elif a['s'] == True:
        do_query(
            ScheduleContext,
            machine = a['machine'],
            fmt = a['f'],
            helper = GenericEpisodeHelper
        )
    else:
        _invoke_search(' '.join(a['query']), a, cache = cache, **kwargs)


def main():
    parser = argparse.ArgumentParser(
        # conflict_handler = 'resolve',
        # allow_abbrev = False
    )
    _arg_parse_common(parser)
    _argparse(parser)
    args = DStorBase(vars(parser.parse_known_args()[0]))

    if args.get('test'):
        return run_generic_test()

    if args.get('d') == True:
        set_loglevel(logging.DEBUG)

    config = ConfigParser()
    config.read(args['c'] if args['c'] else CONFIG_FILE)

    cache_file = args.get('cache', None)

    if not cache_file:
        cache_file = config.get(
            'tvmaze',
            'database_file',
            fallback = None
        )

    if cache_file:
        cache = IStor(cache_file, STORAGE_SCHEMA)

        logger.debug('Cache initialized')

        if args.get('cache_expire'):
            cache.data['cache_expire_time'] = int(args['cache_expire'])
        else:
            cache.data['cache_expire_time'] = config.getint('tvmaze', 'cache_expire_time', fallback = 86400)

    else:
        cache = None

    try:
        _main(args, config, cache = cache)
    except KeyboardInterrupt:
        pass
    except BaseNotFoundException as e:
        logger.error(e)
    except BaseException as e:
        logger.exception(e)
        return 1
    finally:
        if cache:
            cache.close()

    return 0
