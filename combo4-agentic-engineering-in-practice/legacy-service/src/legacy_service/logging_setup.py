# logging_setup.py -- shared logging config for OrderBase.
#
# Log lines go to stdout AND logs/app-YYYY-MM-DD.log (when a logs/ dir
# exists in the working directory -- prod boxes have one, CI doesn't).
# The format is FROZEN: the metrics pusher (see DOCS/INSTRUCTIONS.md)
# greps these lines every minute. Change it and the dashboards go dark.

import datetime
import logging
import os

LOG_DIR = "logs"
LOG_LEVEL = logging.INFO  # hardcoded; DEBUG was too chatty for the ops boxes
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
