import requests, json, datetime

BASEURL = "http://api.tvmaze.com"

RESULT_TYPE_NORMAL = 0
RESULT_TYPE_SEARCH = 1
RESULT_TYPE_PERSON = 2
RESULT_TYPE_SCHEDULE = 3
RESULT_TYPE_LOOKUP = 4
RESULT_TYPE_EPISODES = 5


class TResultBase():

    def __init__(self, data):
        if not isinstance(data, dict):
            raise TypeError("TVMaze result expected dictionary")

        self.__data = data

    def __getitem__(self, key):
        return self.__data[key] if key in self.__data else None

    def __str__(self):
        return str(self.__data)

    def __getattr__(self, key):
        return self.__data[key] if key in self.__data else None


class TResultGeneric(TResultBase):

    def __init__(self, data):

        TResultBase.__init__(self, data)

        def wrap_list_recursive(l):
            for i, v in enumerate(l):
                if isinstance(v, dict):
                    l[i] = TResultGeneric(v)
                elif isinstance(v, list):
                    wrap_list_recursive(v)

        for k, v in data.items():
            if isinstance(v, dict):
                data[k] = TResultGeneric(v)
            elif isinstance(v, list):
                wrap_list_recursive(v)


class TResult(TResultBase):

    def __init__(self, data, restype = RESULT_TYPE_NORMAL):

        TResultGeneric.__init__(self, data)

        if restype == RESULT_TYPE_LOOKUP:
            self.show = self

        self._restype = restype

        self.setup_convenience_shortcuts()

    def setup_convenience_shortcuts(self):

        if self.network != None:
            self.network_name = self.network.name
            if self.network.country != None:
                self.network_country = self.network.country.name
                self.network_country_code = self.network.country.code

        elif self.webChannel != None:
            self.network_country = self.webChannel.country
            self.network_name = self.webChannel.name

        if self._embedded != None:
            if self._embedded.episodes != None:
                self.episodes = self._embedded.episodes


class TResultMulti():

    def __init__(self, data, restype):
        if not isinstance(data, list):
            raise TypeError("TVMaze query result expected list")

        self.data = []
        for v in data:
            self.data.append(TResult(v, restype))

    def parse(self):
        raise Exception("Not implemented")

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __str__(self):
        return '<{} (results={})>'.format(
            self.__class__.__name__,
            len(self.data)
        )


class TBaseNotFoundException(Exception):
    pass


class TBase():
    URL = None

    def __init__(self, cache = None):
        self.cache = cache

    def query(self, *args, **kwargs):
        raise Exception("Not implemented")

    def fetch(self, url = None):
        r = requests.get(url)

        if r.status_code == 404:
            raise TBaseNotFoundException('Not found')

        if r.status_code != 200:
            raise Exception("Query failed: {}".format(r.status_code))

        return json.loads(r.text)


SEARCH_MODE_SINGLE = 1
SEARCH_MODE_MULTI = 2


class TSearchContext(TBase):

    def __init__(self, mode, embed = None, *args, **kwargs):
        TBase.__init__(self, *args, **kwargs)

        if mode == SEARCH_MODE_SINGLE:
            self.URL = BASEURL + "/singlesearch/shows?q={}"

            if embed != None:
                self.URL += '&embed={}'.format(embed)
        elif mode == SEARCH_MODE_MULTI:
            self.URL = BASEURL + "/search/shows?q={}"
        else:
            raise Exception("Unknown search mode: {}".format(mode))

    def query(self, string):

        data = self.fetch(self.URL.format(string))

        if (isinstance(data, list)):
            return TResultMulti(data, RESULT_TYPE_SEARCH)
        elif (isinstance(data, dict)):
            return TResult(data, RESULT_TYPE_LOOKUP)
        else:
            raise Exception("???")


class TLookupContext(TBase):

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
                self.URL += '?embed={}'.format(embed)
        else:
            raise Exception("Unsupported lookup mode")

    def query(self, string):
        return TResult(
            self.fetch(self.URL.format(string)),
            RESULT_TYPE_LOOKUP
        )


class TScheduleContext(TBase):
    URL = BASEURL + "/schedule"

    def query(self, *args, **kwargs):
        return TResultMulti(
            self.fetch(self.URL),
            RESULT_TYPE_SCHEDULE
        )


class TPeopleContext(TBase):
    URL = BASEURL + "/search/people?q={}"

    def query(self, string):
        return TResultMulti(
            self.fetch(self.URL.format(string)),
            RESULT_TYPE_PERSON
        )


def stamptodt(ts):
    return datetime.datetime.strptime(ts[:-3] + ts[-2:], "%Y-%m-%dT%H:%M:%S%z")
