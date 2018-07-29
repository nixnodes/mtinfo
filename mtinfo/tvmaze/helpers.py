
from .tvmaze import (
    ResultBaseHelper,
    Result,

    stamptodt,

    RESULT_TYPE_EPISODE,

    RESULT_TYPE_PERSON,
    RESULT_TYPE_LOOKUP,
    RESULT_TYPE_SEARCH,
    RESULT_TYPE_SCHEDULE
)
from ..misc import strip_tags
from ..helpers import fmt_time

import calendar, time


def deltat(airstamp):
    return calendar.timegm(stamptodt(airstamp).utctimetuple()) - time.time()


class GenericEpisodeHelper(ResultBaseHelper):
    keys = [
        'show',
        'name',
        'season',
        'number',
        'local_airtime',
        'local_airtime_d',
        'summary',
        'eta'
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
            result._bind_key('eta', fmt_time(deltat(result.data.airstamp)))
            result._bind_key('local_airtime_d', '{} ({})'.format(result.local_airtime, result.eta))

        if result.data.summary:
            result._bind_key(
                'summary',
                strip_tags(result.data.summary)
                    if isinstance(result.data.summary, str)
                    else None
            )


class GenericShowHelper(ResultBaseHelper):

    keys = [
        'network_name',
        'network_country',
        'network_country_code',
        'genres',
        'schedule',
        'previousepisode',
        'nextepisode',
        '_nextepisode',
        'nextepisode_utc',
        'name',
        'url',
        'type',
        'runtime',
        'language',
        'summary',
        'episodes',
        'rating',
        'nextepisode_airstamp',
        'nextepisode_airtime',
        'nextepisode_deltat'
    ]

    def format_episode_info(self, d):
        if not d:
            return d

        return (
            "S{}E{} {} on {}".format(
                d.season,
                d.number,
                d.name,
                '{} ({})'.format(
                    stamptodt(d.airstamp).strftime("%d-%m-%Y at %H:%M %Z"),
                    fmt_time(deltat(d.airstamp))
                )
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
            result._bind_key(
                'summary',
                strip_tags(result.data.summary)
                    if isinstance(result.data.summary, str)
                    else None
            )

        result._bind_key('previousepisode', self.format_episode_info(
            result.data._embedded.previousepisode
        ))
        result._bind_key('nextepisode', self.format_episode_info(
            result.data._embedded.nextepisode
        ))

        if result.data._embedded.nextepisode:
            result._bind_key('_nextepisode',
                Result(
                    result.data._embedded.nextepisode._rawdata_,
                    RESULT_TYPE_EPISODE,
                    helper = GenericEpisodeHelper
                )
            )

            result._bind_key('nextepisode_airtime',
                stamptodt(result.data._embedded.nextepisode.airstamp).strftime("%d-%m-%Y at %H:%M %Z")
            )

            result._bind_key('nextepisode_deltat',
                fmt_time(deltat(result.data._embedded.nextepisode.airstamp))
            )

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


def print_informative(r):

    if (r._restype_ == RESULT_TYPE_SEARCH or
         r._restype_ == RESULT_TYPE_LOOKUP):

        print('Name: {}\nURL: {}\nNetwork: {}\nRating: {}\nCountry: {}\nCC: {}\nLanguage: {}\nType: {}\nGenres: {}\nSchedule: {}\nRuntime: {} min\nPrevious: {}\nNext: {}\nSummary: {}'.format(
            r.name,
            r.url,
            r.network_name,
            r.rating,
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

        # if r.episodes != None:
        #    for v in r.episodes:
        #        print('    {} | {} ({}x{})'.format(
        #            v.local_airtime,
        #            v.name,
        #            v.season, v.number
        #        ))

    elif (r._restype_ == RESULT_TYPE_PERSON):
        print('{} - {}'.format(
            r.data.person.name,
            r.data.person.url
        ))
    elif (r._restype_ == RESULT_TYPE_SCHEDULE):
        print('{} | {} - {} (S{}E{}) - [{} - {}] - {}min | {}'.format(
            r.local_airtime_d ,
            r.show.name,
            r.name,
            r.season, r.number,
            r.show.type,
            r.show.genres,
            r.data.runtime,
            r.summary
        ))
