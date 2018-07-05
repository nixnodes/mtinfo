
from .tvmaze import (
    ResultBaseHelper,
    Result,

    stamptodt,

    RESULT_TYPE_EPISODE,
    RESULT_TYPE_LOOKUP
)
from ..misc import strip_tags


class GenericEpisodeHelper(ResultBaseHelper):
    keys = [
        'show',
        'name',
        'season',
        'number',
        'local_airtime',
        'summary'
    ]

    def do(self, result):
        if result.data.show:
            result._bind_key(
                'show',
                Result(
                    result.data.show._rawdata_,
                    RESULT_TYPE_LOOKUP,
                    helper = GenericShowHelper
                )
            )

        result._bind_key('name', result.data.name)
        result._bind_key('season', result.data.season)
        result._bind_key('number', result.data.number)

        if result.data.airstamp:
            result._bind_key('local_airtime', stamptodt(result.data.airstamp).strftime("%d-%m-%Y at %H:%M"))

        if result.data.summary:
            result._bind_key('summary', strip_tags(result.data.summary) if isinstance(result.data.summary, str) else None)


class GenericShowHelper(ResultBaseHelper):

    keys = [
        'network_name',
        'network_country',
        'network_country_code',
        'genres',
        'schedule',
        'previousepisode',
        'nextepisode',
        'name',
        'url',
        'type',
        'runtime',
        'language',
        'summary',
        'episodes',
        'rating'
    ]

    def format_episode_info(self, d):
        if not d:
            return d
        return (
            "{}x{} {} on {}".format(
                d.season,
                d.number,
                d.name,
                stamptodt(d.airstamp).strftime("%d-%m-%Y at %H:%M")
            )
        )

    def do(self, result):

        if result.data.network != None:
            result._bind_key('network_name', result.data.network.name)
            if result.data.network.country != None:
                result._bind_key('network_country', result.data.network.country.name)
                result._bind_key('network_country_code', result.data.network.country.code)

        elif result.data.webChannel != None:
            result._bind_key('network_name', result.data.webChannel.name)
            if result.data.webChannel.country:
                result._bind_key('network_country', result.data.webChannel.country.name)
                result._bind_key('network_country_code', result.data.webChannel.country.code)

        if isinstance(result.data.genres, list):
            result._bind_key('genres', ', '.join(result.data.genres))
        else:
            result._bind_key('genres', result.data.genres)

        if result.data.schedule:
            result._bind_key('schedule', '{}{}'.format(
                ', '.join(result.data.schedule.days) if result.data.schedule.days else 'Days not known',
                ' at {}'.format(result.data.schedule.time) if result.data.schedule.time else ''
            ))

        if result.data.summary:
            result._bind_key('summary', strip_tags(result.data.summary) if isinstance(result.data.summary, str) else None)

        result._bind_key('previousepisode', self.format_episode_info(
            result.data._embedded.previousepisode
        ))
        result._bind_key('nextepisode', self.format_episode_info(
            result.data._embedded.nextepisode
        ))

        result._bind_key('name', result.data.name)
        result._bind_key('url', result.data.url)
        result._bind_key('type', result.data.type)
        result._bind_key('runtime', result.data.runtime)
        result._bind_key('language', result.data.language)
        result._bind_key('rating', result.data.rating.average)

        if result.data._embedded.episodes:
            o = []
            for v in result.data._embedded.episodes:
                o.append(Result(
                    v._rawdata_,
                    RESULT_TYPE_EPISODE,
                    helper = GenericEpisodeHelper
                ))
            result._bind_key('episodes', o)
