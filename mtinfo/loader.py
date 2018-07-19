
from .arg import arg_parse_common
from .data import DStorBase

import argparse, logging

from .tvmaze.main import main as tvmaze_run
from .irc import run_client as run_irc_client
from .istor_schema import get as schema_get
from .cache import IStor

from .tvmaze.irc import TVMazeIRCCP

from .logging import set_loglevel, Logger
from configparser import ConfigParser

CONFIG_FILE = '/etc/mtinfo.conf'

logger = Logger(__name__)


def load():
    parser = argparse.ArgumentParser()

    arg_parse_common(parser)

    args = DStorBase(vars(parser.parse_known_args()[0]))

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
        cache = IStor(cache_file, schema_get())

        logger.debug('Cache initialized')

        if args.get('cache_expire'):
            cache.data['cache_expire_time'] = int(args['cache_expire'])
        else:
            cache.data['cache_expire_time'] = config.getint('tvmaze', 'cache_expire_time', fallback = 86400)

    else:
        cache = None

    return parser, config, cache


def tvmaze():
    parser, config, cache = load()

    try:
        return tvmaze_run(parser, config, cache)
    finally:
        if cache:
            cache.close()


def irc():
    parser, config, cache = load()

    cpcs = [
        TVMazeIRCCP(cache)
    ]

    try:
        return run_irc_client(parser, config, cache = cache, cpcs = cpcs)
    finally:
        if cache:
            cache.close()
