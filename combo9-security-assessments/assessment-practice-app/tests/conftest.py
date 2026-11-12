# Point the app at a scratch database BEFORE anything imports config/db.
# pytest loads this file before the test modules, so import order is safe.

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="orderbase-test-")
os.environ["ORDERBASE_DB"] = os.path.join(_TMP, "test.db")
