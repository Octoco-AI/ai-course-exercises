# config.py -- runtime settings for OrderBase.
#
# Everything reads from the environment first, so the same code runs on a
# laptop, in CI and in the container image.

import os

APP_VERSION = "1.5.0"

# Loopback unless told otherwise. The container image overrides the host.
HOST = os.environ.get("ORDERBASE_HOST", "127.0.0.1")
PORT = int(os.environ.get("ORDERBASE_PORT", "5057"))
DEBUG = os.environ.get("ORDERBASE_DEBUG", "0") == "1"

# The test rig points this at a scratch database.
DB_PATH = os.environ.get("ORDERBASE_DB", "orderbase.db")

# Seed the local demo accounts into an empty database. The container image
# turns this off.
DEMO_USERS = os.environ.get("ORDERBASE_DEMO_USERS", "1") == "1"

# Service account for the nightly fulfilment sync, which pushes status
# updates back into OrderBase. Set ORDERBASE_WMS_SYNC_TOKEN in the
# environment; the fallback keeps the sync working on boxes that predate
# the env file.
_DEFAULT_WMS_SYNC_TOKEN = "obsvc_7Qm2xK9pLr4TzW8vN3bY6cJ1hD5gF0aS"
WMS_SYNC_TOKEN = os.environ.get("ORDERBASE_WMS_SYNC_TOKEN", _DEFAULT_WMS_SYNC_TOKEN)
