#!/usr/bin/python3

import sys, logging
from ..tvmaze import (
    LookupContext,
    SEARCH_MODE_SINGLE,
    STORAGE_SCHEMA,
    BaseNotFoundException,
    TBaseHTTPError
)
from ..helpers import GenericShowHelper
from ...cache import IStor

from ...logging import set_loglevel

set_loglevel(logging.DEBUG)


def run():
    querystring = '82'

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

    try:
        result = context.query(querystring)

        print('Name: {}\nURL: {}\nNetwork: {}\nCountry: {}\nCC: {}\nLanguage: {}\nType: {}\nGenres: {}\nSchedule: {}\nRuntime: {} min\nPrevious: {}\nNext: {}'.format(
            result.name,
            result.url,
            result.network_name,
            result.network_country,
            result.network_country_code,
            result.language,
            result.type,
            result.genres,
            result.schedule,
            result.runtime,
            result.previousepisode,
            result.nextepisode,
        ))

        for ep in result.episodes:
            print('\tS{}E{} ({}) local airtime {}'.format(
                ep.season,
                ep.number,
                ep.name,
                ep.local_airtime
            ))

    except BaseNotFoundException:
        # we catch the exception thrown on a 404, inform the user and exit normally
        print('Nothing found')
    except TBaseHTTPError as e:
        print (e)

    cache.close()
    sys.exit(0)
