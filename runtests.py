from subprocess import call
from os import remove

CACHE_FILE = "/tmp/mtinfo_runtests.db"


def run(s):
    a = s.split(' ')
    o = [
        "python",
        "./mtinfo/tvmaze/run.py",
        "--cache",
        CACHE_FILE
    ]
    o.extend(a)
    if call(o) != 0:
        raise Exception("Test failed: {}".format(o))


try:
    run('-i 82 -e')
    run('game of thrones')
    run('-m game of thrones -e')
    run('-p adam')
    run('-list')
    run('-s')
finally:
    try:
        remove(CACHE_FILE)
    except BaseException as e:
        print(e)
        