import threading
import copy


class Flags():

    def __init__(self):
        self._val = 0
        self._lock = threading.Lock()

    def __str__(self):
        return hex(self._val)

    def get(self, mask):
        with self._lock:
            return self._val & mask

    def has(self, mask):
        with self._lock:
            return (self._val & mask) != 0

    def set(self, mask):
        with self._lock:
            self._val |= mask
            return self._val

    def clear(self, mask):
        with self._lock:
            self._val &= ~mask
            return self._val


class DStorBase():

    def __init__(self, data = None):
        self.__datastor = copy.deepcopy(data) if isinstance(data, dict) else {}
        self.__datastor_lock = threading.RLock()

    def __contains__(self, key):
        return self.has(key)

    def __delitem__(self, key):
        self.delete(key)

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        self.set(key, value)

    def __len__(self):
        return len(self.__datastor)

    def __iter__(self):
        return iter(self.__datastor.values())

    def __enter__(self):
        self.__datastor_lock.acquire()

    def __exit__(self, *a):
        self.__datastor_lock.release()

    def __str__(self):
        return str(self.__datastor)

    def keys(self):
        return self.__datastor.keys()

    def items(self):
        return self.__datastor.items()

    def values(self):
        return self.__datastor.values()

    def get(self, key , default = None):
        with self.__datastor_lock:
            if key in self.__datastor:
                return self.__datastor[key]
            else:
                return default

    def has(self, key):
        with self.__datastor_lock:
            return key in self.__datastor

    def mod(self, key, val):
        with self.__datastor_lock:
            self.__datastor[key] += val

    def set(self, key, data):
        with self.__datastor_lock:
            self.__datastor[key] = data

    def create(self, key, data):
        with self.__datastor_lock:
            if not key in self.__datastor:
                self.__datastor[key] = data

    def setdict(self, data):
        self.__datastor = data

    def getdict(self):
        with self.__datastor_lock:
            return copy.copy(self.__datastor)

    def delete(self, key):
        with self.__datastor_lock:
            if key in self.__datastor:
                del self.__datastor[key]

    def clear(self):
        self.__datastor = {}


class DataStorage(DStorBase):

    def __init__(self, data = None):
        DStorBase.__init__(self, data)

    def get_lock(self):
        return self.__datastor_lock

    def get_size(self):
        with self.__datastor_lock:
            return len(self.__datastor)

    def get_copy(self):
        with self.__datastor_lock:
            return copy.deepcopy(self.__datastor)

