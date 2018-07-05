import logging, argparse, json, time

from ..logging import set_loglevel, Logger
from ..arg import _arg_parse_common
from ..cache import IStor

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
    RESULT_TYPE_SEARCH,
    RESULT_TYPE_PERSON ,
    RESULT_TYPE_SCHEDULE,
    RESULT_TYPE_LOOKUP,

    SEARCH_MODE_SINGLE,
    SEARCH_MODE_MULTI,

    ResultJSONEncoder,

    STORAGE_SCHEMA
)

from .helpers import (
    GenericShowHelper,
    GenericEpisodeHelper
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
    parser.add_argument('-c', type = str, nargs = '?', help = 'Config file')
    parser.add_argument('-b', type = str, nargs = '?', help = 'Batch file')
    parser.add_argument('-list', action = 'store_true', help = 'List cache')
    parser.add_argument('--cache_expire', type = int, nargs = '?', help = 'Cache expiration time')
    parser.add_argument('--rate_limit', type = str, nargs = '?', help = 'Query rate limit')
    parser.add_argument('query', nargs = '*')


def print_informative(r):

    if (r._restype_ == RESULT_TYPE_SEARCH or
         r._restype_ == RESULT_TYPE_LOOKUP):

        print('Name: {}\nURL: {}\nNetwork: {}\nCountry: {}\nCC: {}\nLanguage: {}\nType: {}\nGenres: {}\nSchedule: {}\nRuntime: {} min\nPrevious: {}\nNext: {}\nSummary: {}'.format(
            r.name,
            r.url,
            r.network_name,
            r.network_country,
            r.network_country_code,
            r.language,
            r.type,
            r.genres,
            r.schedule,
            r.runtime,
            r.previousepisode,
            r.nextepisode,
            r.summary
        ))

        if r.episodes != None:
            for v in r.episodes:
                print('    {} | {} ({}x{})'.format(
                    v.local_airtime,
                    v.name,
                    v.season, v.number
                ))

    elif (r._restype_ == RESULT_TYPE_PERSON):
        print('{} - {}'.format(
            r.data.person.name,
            r.data.person.url
        ))
    elif (r._restype_ == RESULT_TYPE_SCHEDULE):
        print('{} | {} - {} ({}x{}) - [{} - {}] - {}min | {}'.format(
            r.local_airtime,
            r.show.name,
            r.name,
            r.season, r.number,
            r.show.type,
            r.show.genres,
            r.data.runtime,
            r.summary
        ))


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


def lookup_show(*args, embed = None, **kwargs):

    e = [
        'nextepisode',
        'previousepisode'
    ]

    if embed:
        e.extend(embed)

    do_query(
        *args,
        **kwargs,
        embed = e,
    )


def do_list(cache, **kwargs):
    for v in cache.getall('shows'):
        result = Result(
            json.loads(v['data']),
            restype = RESULT_TYPE_LOOKUP,
            helper = GenericShowHelper,
        )
        _do_print(result, **kwargs)


def _do_search(qs, a, cache, **kwargs):

    if a['i']:
        lookup_show(
            LookupContext,
            q = qs,
            machine = a['machine'],
            fmt = a['f'],
            mode = 'tvmaze',
            embed = ['episodes'] if a['e'] else None,
            helper = GenericShowHelper,
            cache = cache,
            **kwargs
        )
    elif (a['l'] != None):
        lookup_show(
            LookupContext,
            q = qs,
            machine = a['machine'],
            fmt = a['f'],
            mode = a['l'],
            embed = ['episodes'] if a['e'] else None,
            helper = GenericShowHelper,
            cache = cache,
            **kwargs
        )
    elif (a['p'] == True):
        do_query(
            PeopleContext,
            q = qs,
            fmt = a['f'],
            machine = a['machine'],
            cache = cache,
            **kwargs
        )
    else:
        lookup_show(
            SearchContext,
            mode = SEARCH_MODE_MULTI if a['m'] else SEARCH_MODE_SINGLE,
            q = qs,
            machine = a['machine'],
            fmt = a['f'],
            embed = ['episodes'] if a['e'] else None,
            helper = GenericShowHelper,
            cache = cache,
            **kwargs
        )


def _invoke_search(qs, a, cache):

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

        with open(a['b'], 'r') as f:

            for l in f:
                l = l.rstrip()
                if len(l) == 0:
                    continue

                try:
                    sr += 1
                    # pt = time.monotonic()
                    _do_search(l, a, cache, rlcallback = lambda: rlcallback(_rlst))
                except BaseNotFoundException as e:
                    logger.error(e)
    else:

        if (len(qs) == 0):
            raise Exception("Missing query")

        _do_search(qs, a, cache)


def _main(a, config, cache):

    if a['cache_expire']:
        cache.data['cache_expire_time'] = int(a['cache_expire'])
    else:
        cache.data['cache_expire_time'] = config.getint('tvmaze', 'cache_expire_time', fallback = 86400)

    embed = []

    if a['e']:
        embed.append('episodes')

    if a['list']:
        do_list(
            cache,
            machine = a['machine'],
            fmt = a['f'],
        )
    elif a['s'] == True:
        do_query(
            ScheduleContext,
            machine = a['machine'],
            fmt = a['f'],
            helper = GenericEpisodeHelper
        )
    else:

        _invoke_search(' '.join(a['query']), a, cache)


def main():
    parser = argparse.ArgumentParser(
        conflict_handler = 'resolve',
        # allow_abbrev = False
    )
    _arg_parse_common(parser)
    _argparse(parser)
    a = vars(parser.parse_known_args()[0])

    if a['d'] == True:
        set_loglevel(logging.DEBUG)

    config = ConfigParser()
    config.read(a['c'] if a['c'] else CONFIG_FILE)

    cache_file = config.get('tvmaze', 'database_file', fallback = None)

    if cache_file:
        cache = IStor(cache_file, STORAGE_SCHEMA)
    else:
        cache = None

    try:
        _main(a, config, cache)
    except KeyboardInterrupt:
        pass
    except BaseNotFoundException as e:
        logger.error(e)
    finally:
        if cache:
            cache.close()

