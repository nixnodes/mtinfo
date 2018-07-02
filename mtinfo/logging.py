import logging

from .debug import debug_trace

import sys, copy

try:
    import coloredlogs

    _cllvlstyles = copy.deepcopy(coloredlogs.DEFAULT_LEVEL_STYLES)
    _cllvlstyles['exception'] = {'color': 'magenta'}

    _clflstyles = copy.deepcopy(coloredlogs.DEFAULT_FIELD_STYLES)
    _clflstyles['name'] = {'color': 'cyan'}

    coloredlogs.install (
            level = logging.INFO,
            stream = sys.stderr,
            fmt = '[%(levelname)s @ %(name)s] %(message)s',
            field_styles = _clflstyles,
            level_styles = _cllvlstyles
)

    def set_loglevel(level):
        logging.getLogger().setLevel(level)
        coloredlogs.set_level(level)

except (KeyboardInterrupt, SystemExit):
    raise
except BaseException as e:
    logging.basicConfig (
                level = logging.INFO,
                stream = sys.stderr,
                format = '[%(levelname)s @ %(name)s] %(message)s',
            )

    def set_loglevel(level):
        logging.getLogger().setLevel(level)

EXCEPTION_LEVELV_NUM = 200
logging.addLevelName(EXCEPTION_LEVELV_NUM, "EXCEPTION")


def _exceptv(self, message, *args, **kws):
    if self.isEnabledFor(EXCEPTION_LEVELV_NUM):
        self._log(EXCEPTION_LEVELV_NUM, message, args, **kws)


logging.Logger.exceptv = _exceptv

#logging.getLogger('urllib3').propagate = False


class Logger:

    def __init__(self, name, propagate = True):
        self.logger = logging.getLogger(name)
        self.logger.propagate = propagate

    def get(self):
        return self.logger

    def set_level(self, level):
        self.logger.setLevel(level)

    # ' '.join(list(msg))
    def _process_args(self, *a):
        l = list(a)
        for i, v in enumerate(l):
            if not isinstance(v, str):
                l[i] = str(v)
        return ' '.join(l)

    def debug(self, *msg):
        self.logger.debug(self._process_args(*msg))

    def error(self, *msg):
        self.logger.error(self._process_args(*msg))

    def info(self, *msg):
        self.logger.info(self._process_args(*msg))

    def warn(self, *msg):
        self.logger.warning(self._process_args(*msg))

    def log(self, lvl, *msg, **kwargs):
        self.logger.log(
                lvl,
                self._process_args(*msg),
                extra = kwargs['extra'] if 'extra' in kwargs else None
            )

    def exception(self, *msg):
        debug_trace()
        self.logger.exceptv(self._process_args(*msg))
