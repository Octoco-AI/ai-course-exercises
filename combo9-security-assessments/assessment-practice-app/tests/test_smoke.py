# Smoke tests. Thin on purpose -- they check the service turns on.

import os
import tempfile
import unittest

# Scratch database before anything imports db.py. conftest.py does the same
# under pytest; this keeps `python -m unittest` working too.
if "ORDERBASE_DB" not in os.environ:
    os.environ["ORDERBASE_DB"] = os.path.join(
        tempfile.mkdtemp(prefix="orderbase-test-"), "test.db")

from legacy_service import db  # noqa: E402
from legacy_service.app import app  # noqa: E402

ALICE = {"Authorization": "Bearer alice-dev-token"}


class SmokeTest(unittest.TestCase):

    def setUp(self):
        db.init_db()
        self.client = app.test_client()

    def _create_order(self):
        return self.client.post("/orders", headers=ALICE, json={
            "customer": "Smoke Test Co",
            "items": [{"sku": "SKU-0001", "qty": 1, "unit_price": 19.99}],
        })

    def test_create_order(self):
        resp = self._create_order()
        self.assertEqual(resp.status_code, 201)
        body = resp.get_json()
        self.assertEqual(len(body["id"]), 8)
        self.assertEqual(body["status"], "NEW")
        self.assertEqual(body["total"], 19.99)

    def test_get_order(self):
        order_id = self._create_order().get_json()["id"]
        resp = self.client.get("/orders/%s" % order_id, headers=ALICE)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["customer"], "Smoke Test Co")

    def test_list_orders(self):
        order_id = self._create_order().get_json()["id"]
        resp = self.client.get("/orders", headers=ALICE)
        self.assertEqual(resp.status_code, 200)
        ids = [o["id"] for o in resp.get_json()["orders"]]
        self.assertIn(order_id, ids)

    def test_health(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "ok")


if __name__ == "__main__":
    unittest.main()
