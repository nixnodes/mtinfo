from subprocess import call
from os import remove, path

CACHE_FILE = "/tmp/mtinfo_runtests.db"


def run(s):
    a = s.split(' ')
    o = [
        "python",
        "mtinfo/tvmaze/run.py",
        "-d",
        "--cache",
        CACHE_FILE
    ]
    o.extend(a)
    print('Running test: {}'.format(' '.join(o)))
    if call(o) != 0:
        raise Exception("Test failed: {}".format(o))

try:
    run('-i 1 -e')
    run('-m game of thrones')
    run('game of thrones')
    run('-p adam')
    run('-list -f {name}')
    run('-s')
    print('OK: All tests succeeded.')
finally:
    try:
        if path.exists(CACHE_FILE):
            remove(CACHE_FILE)
    except BaseException as e:
        print(e)
