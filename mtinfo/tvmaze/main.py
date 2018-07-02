import logging, argparse, json, datetime

from ..logging import set_loglevel, Logger
from ..misc import strip_tags
from ..arg import _arg_parse_common

from mtinfo.tvmaze.tvmaze import (
    TSearchContext,
    TLookupContext,
    TScheduleContext,
    TPeopleContext,
    # RESULT_TYPE_NORMAL,
    RESULT_TYPE_SEARCH,
    RESULT_TYPE_PERSON ,
    RESULT_TYPE_SCHEDULE,
    RESULT_TYPE_LOOKUP,

    SEARCH_MODE_SINGLE,
    SEARCH_MODE_MULTI
)

logger = Logger(__name__)


def _argparse(parser):
    # parser.add_argument('-bla', type = str, nargs = '?')
    parser.add_argument('-machine', action = 'store_true', help = 'Machine-readable output')
    parser.add_argument('-l', type = str, nargs = '?', help = 'Lookup by foreign ID [imdb|tvrage|thetvdb]')
    parser.add_argument('-i', type = str, nargs = '?', help = 'Lookup by ID')
    parser.add_argument('-s', action = 'store_true', help = 'Today\'s schedule (US)')
    parser.add_argument('-p', action = 'store_true', help = 'Search people')
    parser.add_argument('-e', action = 'store_true', help = 'Embed episodes in query result')
    parser.add_argument('-m', action = 'store_true', help = 'Multiple results on search')
    parser.add_argument('query', nargs = '*')


def print_informative(r):

    if (r._restype == RESULT_TYPE_SEARCH or
         r._restype == RESULT_TYPE_LOOKUP):

        print('{} ({}) - [{} - {}] - {}min | {}'.format(
            r.show.name,
            r.show.language,
            r.show.type,
            '|'.join(r.show.genres) if len(r.show.genres) > 0 else 'Unknown',
            r.show.runtime,
            strip_tags(r.show.summary) if r.show.summary != None else 'None'
        ))

        if r.episodes != None:
            for v in r.episodes:
                dt = datetime.datetime.strptime(v['airstamp'][:-3] + v['airstamp'][-2:], "%Y-%m-%dT%H:%M:%S%z")

                print('    {} | {} ({}x{})'.format(
                    dt.strftime("%d-%m-%Y %H:%M"),
                    v.name,
                    v.season, v.number
                ))

    elif (r._restype == RESULT_TYPE_PERSON):
        print('{} - {}'.format(
            r.person.name,
            r.person.url
        ))
    elif (r._restype == RESULT_TYPE_SCHEDULE):
        dt = datetime.datetime.strptime(r['airstamp'][:-3] + r['airstamp'][-2:], "%Y-%m-%dT%H:%M:%S%z")

        print('{} | {} - {} ({}x{}) - [{} - {}] - {}min | {}'.format(
            dt.strftime("%d-%m-%Y %H:%M"),
            r.show.name,
            r.name,
            r.season, r.number,
            r.show.type,
            '|'.join(r.show.genres) if len(r.show.genres) > 0 else 'Unknown',
            r.runtime,
            strip_tags(r.summary) if r.summary != None else 'None'
        ))


def do_query(context, q = None, machine = False, **kwargs):
    logger.debug("Query: '{}'".format(q))

    r = context(**kwargs).query(q)

    if machine:
        if isinstance(r.data, list):
            o = []
            for v in r.data:
                o.append(v.data)
            print(json.dumps(o, ensure_ascii = False))
        else:
            print(json.dumps(r.data, ensure_ascii = False))
    else:
        if isinstance(r.data, list):
            for v in r.data:
                print_informative(v)
        else:
            print_informative(r)


def main():
    parser = argparse.ArgumentParser(
        conflict_handler = 'resolve',
        allow_abbrev = False
    )
    _arg_parse_common(parser)
    _argparse(parser)
    a = vars(parser.parse_known_args()[0])

    if (a['d'] == True):
        set_loglevel(logging.DEBUG)

    if (a['i'] != None):
        do_query(
            TLookupContext,
            q = a['i'],
            machine = a['machine'],
            mode = 'tvmaze',
            embed = 'episodes' if a['e'] else None
        )
    elif (a['s'] == True):
        do_query(TScheduleContext, machine = a['machine'])
    else:
        if (len(a['query']) == 0):
            raise Exception("Missing query")

        qs = ' '.join(a['query'])

        if (a['l'] != None):
            do_query(
                TLookupContext, 
                q = qs, 
                machine = a['machine'], 
                mode = a['l'],
                embed = 'episodes' if a['e'] else None
            )
        elif (a['p'] == True):
            do_query(
                TPeopleContext, 
                q = qs, 
                machine = a['machine']
            )
        else:
            do_query(
                TSearchContext,
                mode = SEARCH_MODE_MULTI if a['m'] else SEARCH_MODE_SINGLE,
                q = qs,
                machine = a['machine'],
                embed = 'episodes' if a['e'] else None
            )

