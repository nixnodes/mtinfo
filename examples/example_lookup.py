#!/usr/bin/python3

import sys, logging
import mtinfo.tvmaze.tvmaze as tvmaze
from mtinfo.tvmaze.helpers import GenericShowHelper
from mtinfo.cache import IStor

from mtinfo.logging import set_loglevel

# enable debug logging
set_loglevel(logging.DEBUG)

querystring = ' '.join(sys.argv[1:])

# abort if no command line arguments
if not querystring:
    sys.exit()

# create a sqlite3 interface
cache = IStor("/tmp/tvmaze.db", tvmaze.STORAGE_SCHEMA)

# create a search context
context = tvmaze.SearchContext(
    mode = tvmaze.SEARCH_MODE_SINGLE,
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
except tvmaze.BaseNotFoundException:
    # we catch the exception thrown on a 404, inform the user and exit normally
    print('Nothing found')
    sys.exit(1)

# print result data
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

if result.episodes:
    # print out all episodes too (notice embed = 'episodes' context init option above, without it you don't get an ep list)
    print('Episodes:')

    for ep in result.episodes:
        print('\tS{}E{} ({}) local airtime {}'.format(
            ep.season,
            ep.number,
            ep.name,
            ep.local_airtime
        ))

cache.close()
