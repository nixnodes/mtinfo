from ..irc import BaseCommandProcessor
from .tvmaze import SearchContext, SEARCH_MODE_SINGLE, ResultMulti
from .helpers import GenericShowHelper


class TVMazeIRCCP(BaseCommandProcessor):

    FORMAT_SHOW = '{name} / {rating}'

    def __init__(self, cache = None):
        self.cache = cache

    def cmd_tv(self, client, source, user, *args):
        context = SearchContext(
            mode = SEARCH_MODE_SINGLE,
            embed = [
                'nextepisode',
                'previousepisode',
                'episodes'
            ],
            helper = GenericShowHelper,
            cache = self.cache
        )

        result = context.query(' '.join(args))

        fmt = client.options.get('show_format')
        if not fmt:
            fmt = self.FORMAT_SHOW

        if isinstance(result, ResultMulti):
            for v in result:
                client.message(source, v.format(fmt))
        else:
            client.message(source, result.format(fmt))

