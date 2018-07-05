#!/usr/bin/python3

import sys, logging

from ..tvmaze import (
    LookupContext,
    SearchContext,
    PeopleContext,
    ScheduleContext,
    ResultMulti,
    SEARCH_MODE_SINGLE,
    SEARCH_MODE_MULTI,
    STORAGE_SCHEMA,
    BaseNotFoundException,
    TBaseHTTPError
)

from ..helpers import (
    GenericShowHelper,
    GenericEpisodeHelper,
    print_informative
)

from ...cache import IStor

from ...logging import set_loglevel

set_loglevel(logging.DEBUG)


def query(context, query = None):

    try:
        r = context.query(query)
        if isinstance(r, ResultMulti):
            for v in r:
                print_informative(
                    v
                )
        else:
            print_informative(
                r
            )

    except BaseNotFoundException:
        # we catch the exception thrown on a 404, inform the user and exit normally
        print('Nothing found')
    except TBaseHTTPError as e:
        print (e)


def run():

    cache = IStor("/tmp/tvmaze.db", STORAGE_SCHEMA)

    context = LookupContext(
        mode = 'tvmaze',
        embed = [
            'nextepisode',
            'previousepisode',
            'episodes'
        ],
        helper = GenericShowHelper,
        cache = cache
    )

    query(context, '82')

    context = SearchContext(
        mode = SEARCH_MODE_SINGLE,
        embed = [
            'nextepisode',
            'previousepisode',
            'episodes'
        ],
        helper = GenericShowHelper,
        cache = cache
    )

    query(context, 'game of thrones')

    context = SearchContext(
        mode = SEARCH_MODE_MULTI,
        embed = [
            'nextepisode',
            'previousepisode',
            'episodes'
        ],
        helper = GenericShowHelper,
        cache = cache
    )

    query(context, 'game')

    context = PeopleContext(
        helper = GenericEpisodeHelper,
        cache = cache
    )

    query(context, 'adam')

    context = ScheduleContext(
        helper = GenericEpisodeHelper,
        cache = cache
    )

    query(context)

    cache.close()
    
    print("OK: All tests succeeded")
    
    sys.exit(0)
