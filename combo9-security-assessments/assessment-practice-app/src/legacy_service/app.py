# app.py -- OrderBase HTTP API.
#
# Customers create and track their own orders; staff (and the fulfilment
# sync's service account) can see and change any order.

from flask import Flask, g, jsonify, request

from legacy_service import config, db, orders
from legacy_service.auth import can_access_order, is_staff, require_auth
from legacy_service.logging_setup import get_logger, setup_logging
from legacy_service.utils import normalise_order_id

APP_VERSION = config.APP_VERSION

log = get_logger("legacy_service.app")

app = Flask("orderbase")


def _load_order_for(user, order_id):
    """Return the order if this user may act on it, else None (404)."""
    order = orders.get_order(normalise_order_id(order_id))
    if order is None or not can_access_order(user, order):
        return None
    return order


def _not_found(order_id):
    return jsonify({"error": "order %s not found" % order_id}), 404


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": APP_VERSION})


@app.route("/orders", methods=["POST"])
@require_auth
def create_order():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "body must be JSON"}), 400
    try:
        order = orders.create_order(data, owner_id=g.user["id"],
                                    allow_discount=is_staff(g.user))
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except ValueError as exc:
        log.warning("rejected order: %s", exc)
        return jsonify({"error": str(exc)}), 400
    log.info("POST /orders 201 id=%s total=%.2f", order["id"], order["total"])
    return jsonify(order), 201


@app.route("/orders/<order_id>", methods=["GET"])
@require_auth
def get_order(order_id):
    order_id = normalise_order_id(order_id)
    order = orders.get_order(order_id)
    if order is None:
        log.info("GET /orders/%s 404", order_id)
        return _not_found(order_id)
    log.info("GET /orders/%s 200 status=%s", order_id, order["status"])
    return jsonify(order)


@app.route("/orders", methods=["GET"])
@require_auth
def list_orders():
    status = request.args.get("status")
    limit = request.args.get("limit", "50")
    owner_id = None if is_staff(g.user) else g.user["id"]
    try:
        result = orders.list_orders(status=status, limit=limit, owner_id=owner_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    log.info("GET /orders 200 count=%d", len(result))
    return jsonify({"orders": result, "count": len(result)})


@app.route("/orders/<order_id>", methods=["PATCH"])
@require_auth
def update_order(order_id):
    order = _load_order_for(g.user, order_id)
    if order is None:
        return _not_found(order_id)
    if order["status"] != "NEW" and not is_staff(g.user):
        return jsonify({"error": "only NEW orders can be edited"}), 409
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data:
        return jsonify({"error": "body must be a JSON object"}), 400
    try:
        updated = orders.update_order(order["id"], data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(updated)


@app.route("/orders/<order_id>/cancel", methods=["POST"])
@require_auth
def cancel_order(order_id):
    order = _load_order_for(g.user, order_id)
    if order is None:
        return _not_found(order_id)
    cancellable = ("NEW", "PAID") if is_staff(g.user) else ("NEW",)
    if order["status"] not in cancellable:
        return jsonify({"error": "order is %s and cannot be cancelled"
                        % order["status"]}), 409
    orders.set_status(order["id"], "CANCELLED")
    log.info("POST /orders/%s/cancel 200 by=%s", order["id"], g.user["id"])
    return jsonify(orders.get_order(order["id"]))


# The finance dashboard pulls this every few minutes.
@app.route("/report", methods=["GET"])
def report():
    date_str = request.args.get("date")
    try:
        rep = orders.daily_report(date_str)
    except ValueError:
        return jsonify({"error": "date must be YYYY-MM-DD"}), 400
    log.info("GET /report 200 date=%s orders=%d total=%.2f",
             rep["date"], rep["orders"], rep["total"])
    return jsonify(rep)


def main():
    setup_logging()
    db.init_db()
    print("OrderBase v%s listening on %s:%s (debug=%s)"
          % (APP_VERSION, config.HOST, config.PORT, config.DEBUG))
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG,
            use_reloader=False)


if __name__ == "__main__":
    main()
