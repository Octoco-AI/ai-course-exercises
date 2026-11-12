# Authentication and access tests for the routes that have them.

import os
import tempfile
import unittest

if "ORDERBASE_DB" not in os.environ:
    os.environ["ORDERBASE_DB"] = os.path.join(
        tempfile.mkdtemp(prefix="orderbase-test-"), "test.db")

from legacy_service import db  # noqa: E402
from legacy_service.app import app  # noqa: E402

ALICE = {"Authorization": "Bearer alice-dev-token"}
BOB = {"Authorization": "Bearer bob-dev-token"}
STAFF = {"Authorization": "Bearer staff-dev-token"}

ITEMS = [{"sku": "SKU-0002", "qty": 2, "unit_price": 5.0}]


class AccessTest(unittest.TestCase):

    def setUp(self):
        db.init_db()
        self.client = app.test_client()

    def _order_for(self, headers, **extra):
        body = {"customer": "Access Test", "items": ITEMS}
        body.update(extra)
        resp = self.client.post("/orders", headers=headers, json=body)
        self.assertEqual(resp.status_code, 201, resp.get_json())
        return resp.get_json()

    # --- authentication ---------------------------------------------------

    def test_create_requires_token(self):
        resp = self.client.post("/orders", json={"customer": "x", "items": ITEMS})
        self.assertEqual(resp.status_code, 401)

    def test_list_requires_token(self):
        self.assertEqual(self.client.get("/orders").status_code, 401)

    def test_unknown_token_rejected(self):
        resp = self.client.get("/orders",
                               headers={"Authorization": "Bearer not-a-token"})
        self.assertEqual(resp.status_code, 401)

    def test_wrong_scheme_rejected(self):
        resp = self.client.get("/orders",
                               headers={"Authorization": "Basic alice-dev-token"})
        self.assertEqual(resp.status_code, 401)

    # --- listing ----------------------------------------------------------

    def test_customer_lists_only_own_orders(self):
        alices = self._order_for(ALICE)["id"]
        bobs = self._order_for(BOB)["id"]
        ids = [o["id"] for o in
               self.client.get("/orders?limit=500", headers=BOB).get_json()["orders"]]
        self.assertIn(bobs, ids)
        self.assertNotIn(alices, ids)

    def test_staff_lists_all_orders(self):
        alices = self._order_for(ALICE)["id"]
        bobs = self._order_for(BOB)["id"]
        ids = [o["id"] for o in
               self.client.get("/orders?limit=500", headers=STAFF).get_json()["orders"]]
        self.assertIn(alices, ids)
        self.assertIn(bobs, ids)

    # --- discounts --------------------------------------------------------

    def test_customer_cannot_set_discount(self):
        resp = self.client.post("/orders", headers=ALICE, json={
            "customer": "Access Test", "items": ITEMS, "discount_pct": 50})
        self.assertEqual(resp.status_code, 403)

    def test_staff_can_set_discount(self):
        order = self._order_for(STAFF, discount_pct=10)
        self.assertEqual(order["total"], 9.0)

    # --- cancellation -----------------------------------------------------

    def test_owner_can_cancel(self):
        order_id = self._order_for(ALICE)["id"]
        resp = self.client.post("/orders/%s/cancel" % order_id, headers=ALICE)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "CANCELLED")

    def test_other_customer_cannot_cancel(self):
        order_id = self._order_for(ALICE)["id"]
        resp = self.client.post("/orders/%s/cancel" % order_id, headers=BOB)
        self.assertEqual(resp.status_code, 404)

    def test_staff_can_cancel_any_order(self):
        order_id = self._order_for(ALICE)["id"]
        resp = self.client.post("/orders/%s/cancel" % order_id, headers=STAFF)
        self.assertEqual(resp.status_code, 200)

    def test_cancelled_order_cannot_be_cancelled_again(self):
        order_id = self._order_for(ALICE)["id"]
        self.client.post("/orders/%s/cancel" % order_id, headers=ALICE)
        resp = self.client.post("/orders/%s/cancel" % order_id, headers=ALICE)
        self.assertEqual(resp.status_code, 409)

    # --- editing ----------------------------------------------------------

    def test_owner_can_rename_delivery_contact(self):
        order_id = self._order_for(ALICE)["id"]
        resp = self.client.patch("/orders/%s" % order_id, headers=ALICE,
                                 json={"customer": "Alice at the depot"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["customer"], "Alice at the depot")

    def test_other_customer_cannot_edit(self):
        order_id = self._order_for(ALICE)["id"]
        resp = self.client.patch("/orders/%s" % order_id, headers=BOB,
                                 json={"customer": "Bob"})
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
