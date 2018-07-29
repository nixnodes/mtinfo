import requests, json, time, datetime, calendar

from ..cache import IStor
from ..logging import Logger

BASEURL = "http://api.tvmaze.com"

RESULT_TYPE_NONE = 0
RESULT_TYPE_SEARCH = 1
RESULT_TYPE_PERSON = 2
RESULT_TYPE_SCHEDULE = 3
RESULT_TYPE_LOOKUP = 4
RESULT_TYPE_EPISODE = 5

from ..istor_schema import update as schema_update

schema_update({
    'shows': [
        { 'k' : 'id', 't': 'integer', 'f': 'index'},
        { 'k' : 'td', 't': 'integer', 'f': 'number'},
        { 'k' : 'name', 't': 'text', 'f': 'text'},
        { 'k' : 'type', 't': 'text', 'f': 'text'},
        { 'k' : 'genres', 't': 'text', 'f': 'text'},
        { 'k' : 'country', 't': 'text', 'f': 'text'},
        { 'k' : 'language', 't': 'text', 'f': 'text'},
        { 'k' : 'rating', 't': 'real', 'f': 'number', 'd': 0},
        { 'k' : 'data', 't': 'text', 'f': 'text'},
    ],
})

logger = Logger(__name__)


class ResultJSONEncoder(json.JSONEncoder):

    def default(self, o):
        return o._rawdata_


class ResultBase():

    def __init__(self, data):
        if not isinstance(data, dict):
            raise TypeError("Result expected dictionary")

        self._rawdata_ = data

    def __getitem__(self, key):
        return self._rawdata_[key] if key in self._rawdata_ else None

    def __str__(self):
        return str(self._rawdata_)

    def __getattr__(self, key):
        return self._rawdata_[key] if key in self._rawdata_ else None


class ResultGeneric(ResultBase):

    def __init__(self, data):

        ResultBase.__init__(self, data)

        def wrap_list_recursive(l):
            for i, v in enumerate(l):
                if isinstance(v, dict):
                    l[i] = ResultGeneric(v)
                elif isinstance(v, list):
                    wrap_list_recursive(v)

        for k, v in data.items():
            if isinstance(v, dict):
                data[k] = ResultGeneric(v)
            elif isinstance(v, list):
                wrap_list_recursive(v)


class ResultBaseHelper():

    keys = []

    def __init__(self, result):
        assert isinstance(result, Result)
        for v in self.keys:
            result._bind_key(v, None)
        self.do(result)

    def do(self):
        raise Exception("Not implemented")


class Result():

    def __init__(self, data, restype = RESULT_TYPE_NONE, helper = None, cached = False):

        self.data = ResultGeneric(data)
        self.is_cached = cached

        if self.data._embedded == None:
            self.data._embedded = ResultBase({})

        self._restype_ = restype

        self.__keys = {
            '\\n': '\n'
        }
        self._bind_key('data', self.data)

        if helper != None:
            assert issubclass(helper, ResultBaseHelper)
            helper(self)

    def _bind_key(self, k, d):
        setattr(self, k, d)
        self.__keys[k] = d

    def __getattr__(self, key):
        return self.__keys[key] if key in self.__keys else None

    def format(self, string):
        return string.format(**self.__keys)


class ResultMulti():

    def __init__(self, data, restype, *args, **kwargs):
        if not isinstance(data, list):
            raise TypeError("Query result expected list")

        self.data = []
        for v in data:

            if restype == RESULT_TYPE_SEARCH:
                r = Result(v['show'], restype = restype, *args, **kwargs)
            else:
                r = Result(v, restype = restype, *args, **kwargs)

            self.data.append(r)

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __str__(self):
        return '<{} (results={})>'.format(
            self.__class__.__name__,
            len(self.data)
        )


class BaseHTTPException(Exception):
    pass


class BaseNotFoundException(BaseHTTPException):
    pass


class TBaseHTTPError(BaseHTTPException):

    def __init__(self, msg, code):
        Exception.__init__(self, msg)
        self.httpcode = code


class QueryResult():

    def __init__(self, data, cached = False):
        self.data = data
        self.cached = cached


class rlst():

    DEFAULT_RATE_LIMIT = 2

    def __init__(self, rate_limit = DEFAULT_RATE_LIMIT):
        self.__last_rlcheck = time.monotonic()
        self.__rlcounter = 0
        self.rate_limit = rate_limit if rate_limit != None else self.DEFAULT_RATE_LIMIT

    # def clear(self):
    #    self.__last_rlcheck = time.monotonic()

    def sleep(self, timeout):
        time.sleep(timeout)

    def run(self):

        if time.monotonic() - self.__last_rlcheck > 1:
            self.__last_rlcheck = time.monotonic()
            self.__rlcounter = 0

        while self.__rlcounter / (time.monotonic() - self.__last_rlcheck) > self.rate_limit:
            self.sleep(0.03)

        self.__rlcounter += 1


DEFAULT_CACHE_EXPIRE_TIME = 86400


class TBase():
    URL = None
    clpair = None
    rclass = Result

    def __init__(self, cache = None, helper = None, rlc = None, cache_expire_time = None):

        if cache != None:
            assert isinstance(cache, IStor)
            if cache_expire_time != None:
                self.cache_expire_time = cache_expire_time
            else:
                self.cache_expire_time = cache.data.get(
                    'cache_expire_time',
                    DEFAULT_CACHE_EXPIRE_TIME
                )
        else:
            self.cache_expire_time = DEFAULT_CACHE_EXPIRE_TIME

        if helper != None:
            assert issubclass(helper, ResultBaseHelper)

        if rlc != None:
            assert isinstance(rlc, rlst) or issubclass(rlc, rlst)

        self.cache = cache
        self.helper = helper

        self.__rlc = rlc

        # self._rlcallback = rlcallback

    def httpfetch(self, query = None):

        if self.__rlc:
            self.__rlc.run()

        r = requests.get(self.URL.format(query))

        if r.status_code == 404:
            raise BaseNotFoundException('Not found')

        if r.status_code != 200:
            raise TBaseHTTPError("Query failed: {}".format(r.status_code), r.status_code)

        return json.loads(r.text)

    def cachedump(self, result):

        if (result.is_cached == True):
            return

        if not self.clpair:
            return

        if self.clpair[0] == 'shows':
            logger.debug('Writing cache [{}]..'.format(result.data.id))
            self.cache.set(self.clpair[0], {
                    'id': result.data.id,
                    'td': time.time(),
                    'name': result.data.name,
                    'country': result.network_country,
                    'language': result.data.language,
                    'type': result.data.type,
                    'genres': '|'.join(result.data.genres) if result.data.genres else '',
                    'rating': result.rating,
                    'data': ResultJSONEncoder().encode(result.data)
                }
            )

    def result(self, data, restype, *args, **kwargs):
        assert self.rclass == Result or self.rclass == ResultMulti

        result = self.rclass(data.data, restype, cached = data.cached, *args, **kwargs)

        if self.cache:
            if isinstance(result, ResultMulti):
                for r in result:
                    self.cachedump(r)
            elif isinstance(result, Result):
                self.cachedump(result)

        return result

    def cachefetch(self, query):
        if not self.clpair:
            return None

        e = self.cache.get(
            self.clpair[0],
            self.clpair[1],
            '{}'.format(query),
            sort = 'rating',
            order = 'desc'
        )

        if not e:
            return None

        if isinstance(self.rclass, ResultMulti):
            for v in e:
                if (time.time() - v['td'] > self.cache_expire_time):
                    return None
        else:
            if (time.time() - e[0]['td'] > self.cache_expire_time):
                return None

        return self.load_cache_item(e)

    def load_cache_item(self, e):
        if isinstance(self.rclass, ResultMulti):
            return[ json.loads(x['data']) for x in e]
        else:
            return json.loads(e[0]['data'])

    def fetch(self, query):
        if self.cache:
            data = self.cachefetch(query)
            if data != None:
                logger.debug('Loading from cache [{}]'.format(query))
                return QueryResult(data, cached = True)

        return QueryResult(self.httpfetch(query), cached = False)

    def query(self, query):
        return self.result(
            self.fetch(query),
            self.restype,
            helper = self.helper
        )


SEARCH_MODE_SINGLE = 1
SEARCH_MODE_MULTI = 2


def generate_embed_query_param(d):
    if isinstance(d, str):
        return 'embed={}'.format(d)
    elif isinstance(d, list):
        o = ''
        for i, v in enumerate(d):
            o += 'embed[]={}'.format(v)
            if i < len(d) - 1:
                o += '&'
        return o
    else:
        raise TypeError('Input can only be a string or list')


class SearchContext(TBase):
    clpair = ('shows', 'name')

    def __init__(self, mode, embed = None, *args, **kwargs):
        TBase.__init__(self, *args, **kwargs)

        if mode == SEARCH_MODE_SINGLE:
            self.URL = BASEURL + "/singlesearch/shows?q={}"
            self.rclass = Result

            if embed != None:
                self.URL += '&' + generate_embed_query_param(embed)
        elif mode == SEARCH_MODE_MULTI:
            self.rclass = ResultMulti
            self.URL = BASEURL + "/search/shows?q={}"
        else:
            raise Exception("Unknown search mode: {}".format(mode))

        self.mode = mode

    def query(self, string):

        if self.mode == SEARCH_MODE_MULTI:
            self.restype = RESULT_TYPE_SEARCH
        else:
            self.restype = RESULT_TYPE_LOOKUP

        return TBase.query(self, string)

    def load_cache_item(self, e):
        if self.mode == SEARCH_MODE_MULTI:
            return sorted(
                [ {'show': json.loads(x['data'])} for x in e],
                key = lambda data: float(data['show']['rating']['average']) if data['show']['rating']['average'] != None else 0,
                reverse = True
            )
        else:
            return json.loads(e[0]['data'])


class LookupContext(TBase):
    restype = RESULT_TYPE_LOOKUP
    clpair = ('shows', 'id')
    rclass = Result

    def __init__(self, mode, embed = None, *args, **kwargs):
        TBase.__init__(self, *args, **kwargs)

        if mode == 'tvrage':
            self.URL = BASEURL + "/lookup/shows?tvrage={}"
        elif mode == 'thetvdb':
            self.URL = BASEURL + "/lookup/shows?thetvdb={}"
        elif mode == 'imdb':
            self.URL = BASEURL + "/lookup/shows?imdb={}"
        elif mode == 'tvmaze':
            self.URL = BASEURL + "/shows/{}"
            if embed != None:
                self.URL += '?' + generate_embed_query_param(embed)
        else:
            raise Exception("Unsupported lookup mode")


class ScheduleContext(TBase):
    URL = BASEURL + "/schedule"
    restype = RESULT_TYPE_SCHEDULE
    rclass = ResultMulti

    def __init__(self, *args, **kwargs):
        TBase.__init__(self, *args, **kwargs)

    def query(self, string, time_offset = 0):

        self.URL = BASEURL + '/schedule?date={}'.format(
            datetime.datetime.utcfromtimestamp(
                calendar.timegm(
                    datetime.datetime.utcnow().utctimetuple()
                ) + time_offset
            ).strftime('%Y-%m-%d')
        )

        return TBase.query(self, string)


class PeopleContext(TBase):
    URL = BASEURL + "/search/people?q={}"
    restype = RESULT_TYPE_PERSON
    rclass = ResultMulti


def stamptodt(ts):
    return datetime.datetime.strptime(ts[:-6] + ' ' + ts[-6:-3] + ts[-2:], "%Y-%m-%dT%H:%M:%S %z")
