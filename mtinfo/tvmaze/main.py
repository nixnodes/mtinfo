import logging, argparse

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
    parser.add_argument('-i', type = str, nargs = '?', help = 'Lookup by ID')
    parser.add_argument('-s', action = 'store_true', help = 'Today\'s schedule (US)')
    parser.add_argument('-p', action = 'store_true', help = 'Search people')
    parser.add_argument('-e', action = 'store_true', help = 'Embed episodes in query result')
    parser.add_argument('-m', action = 'store_true', help = 'Multiple results on search')
    parser.add_argument('-f', type = str, nargs = '?', help = 'Format output')
    parser.add_argument('-c', type = str, nargs = '?', help = 'Config file')
    parser.add_argument('--cache_expire', type = int, nargs = '?', help = 'Cache expiration time')
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


def do_query(context, q = None, machine = False, fmt = None, **kwargs):
    logger.debug("Query: '{}'".format(q))

    r = context(**kwargs).query(q)

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


def _main(a, config, cache):

    if a['cache_expire']:
        cache_expire_time = int(a['cache_expire'])
    else:
        cache_expire_time = config.getint('tvmaze', 'cache_expire_time', fallback = 86400)

    embed = []

    if a['e']:
        embed.append('episodes')

    if a['i'] != None:
        lookup_show(
            LookupContext,
            q = a['i'],
            machine = a['machine'],
            fmt = a['f'],
            mode = 'tvmaze',
            embed = ['episodes'] if a['e'] else None,
            helper = GenericShowHelper,
            cache = cache,
            cache_expire_time = cache_expire_time
        )
    elif a['s'] == True:
        do_query(
            ScheduleContext,
            machine = a['machine'],
            fmt = a['f'],
            helper = GenericEpisodeHelper
        )
    else:
        if (len(a['query']) == 0):
            raise Exception("Missing query")

        qs = ' '.join(a['query'])

        if (a['l'] != None):
            lookup_show(
                LookupContext,
                q = qs,
                machine = a['machine'],
                fmt = a['f'],
                mode = a['l'],
                embed = ['episodes'] if a['e'] else None,
                helper = GenericShowHelper,
                cache = cache,
                cache_expire_time = cache_expire_time
            )
        elif (a['p'] == True):
            do_query(
                PeopleContext,
                q = qs,
                fmt = a['f'],
                machine = a['machine'],
                cache = cache
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
                cache_expire_time = cache_expire_time
            )


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
    except BaseNotFoundException as e:
        logger.error(e)
    finally:
        if cache:
            cache.close()

