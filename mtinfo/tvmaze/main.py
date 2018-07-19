import json, sys

from ..logging import Logger

from .tests.generic import run as run_generic_test
from ..data import DStorBase

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
    
    rlst

)

from .helpers import (
    GenericShowHelper,
    GenericEpisodeHelper,
    print_informative
)

logger = Logger(__name__)


def _argparse(parser):
    parser.add_argument('-l', type = str, nargs = '?', help = 'Lookup by foreign ID [imdb|tvrage|thetvdb]')
    parser.add_argument('-i', action = 'store_true', help = 'Lookup by ID')
    parser.add_argument('-s', action = 'store_true', help = 'Today\'s schedule (US)')
    parser.add_argument('-p', action = 'store_true', help = 'Search people')
    parser.add_argument('-e', action = 'store_true', help = 'Embed episodes in query result')
    parser.add_argument('-m', action = 'store_true', help = 'Multiple results on search')


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

        sr = 0

       
        _rlst = rlst(a.get('rate_limit'))


        def procline(l):
            l = l.rstrip()
            if len(l) == 0:
                return 0

            try:
                _do_search(l, a, rlc = _rlst, **kwargs)
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


def _main(a, config, cache = None, **kwargs):

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


def main(parser, config, cache = None):
    _argparse(parser)
    args = DStorBase(vars(parser.parse_known_args()[0]))

    if args.get('test'):
        return run_generic_test()

    try:
        _main(args, config, cache = cache)
    except KeyboardInterrupt:
        pass
    except BaseNotFoundException as e:
        logger.error(e)
    except BaseException as e:
        logger.exception(e)
        return 1

    return 0
