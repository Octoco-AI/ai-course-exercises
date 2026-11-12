# logging_setup.py -- shared logging config for OrderBase.
#
# Log lines go to stdout, and to logs/app-YYYY-MM-DD.log when a logs/ dir
# exists in the working directory.

import datetime
import logging
import os

LOG_DIR = "logs"
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"

_configured = False


def setup_logging():
    global _configured
    if _configured:
        return
    handlers = [logging.StreamHandler()]
    if os.path.isdir(LOG_DIR):
        fname = os.path.join(
            LOG_DIR,
            "app-%s.log" % datetime.date.today().strftime("%Y-%m-%d"),
        )
        handlers.append(logging.FileHandler(fname))
    logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT, handlers=handlers)
    _configured = True


def get_logger(name):
    return logging.getLogger(name)
