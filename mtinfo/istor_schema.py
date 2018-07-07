
__data = {
    'irc': [
        { 'k' : 'id', 't': 'integer', 'f': 'index'},
        { 'k' : 'name', 't': 'text', 'f': 'text'},
        { 'k' : 'type', 't': 'text', 'f': 'text'},
    ],
}


def update(d):
    __data.update(d)


def get():
    return __data
