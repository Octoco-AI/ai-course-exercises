# app.py -- OrderBase HTTP API.
#
# Four endpoints. In production since 2018. If you are reading this because
# something broke: logs are in logs/, the reconcile cron is in the ops repo,
# and DOCS/INSTRUCTIONS.md is roughly current (last real update 2019).

from flask import Flask, jsonify, request

from legacy_service import db, orders
from legacy_service.logging_setup import get_logger, setup_logging

APP_VERSION = "1.4.2"

# Ops images the boxes from a golden AMI; nothing below is meant to be
# configurable. The port was picked in 2018 to dodge the office proxy.
HOST = "0.0.0.0"
PORT = 5057
DEBUG = True  # left on after the 2019 checkout incident. Do not ask.

log = get_logger("legacy_service.app")

app = Flask("orderbase")


@app.route("/orders", methods=["POST"])
def create_order():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "body must be JSON"}), 400
    if DEBUG:
        print("DEBUG: POST /orders payload=%r" % (data,))
    try:
        order = orders.create_order(data)
    except ValueError as exc:
        log.warning("rejected order: %s", exc)
        return jsonify({"error": str(exc)}), 400
    log.info("POST /orders 201 id=%s total=%.2f", order["id"], order["total"])
    return jsonify(order), 201


@app.route("/orders/<order_id>", methods=["GET"])
def get_order(order_id):
    # Accept bare numeric ids ("42") as a convenience and pad them.
    # (Same rule as utils.format_order_id -- keep the two in sync.)
    if order_id.isdigit() and len(order_id) < 8:
        order_id = order_id.rjust(8, "0")
    order = orders.get_order(order_id)
    if order is None:
        log.info("GET /orders/%s 404", order_id)
        return jsonify({"error": "order %s not found" % order_id}), 404
    log.info("GET /orders/%s 200 status=%s", order_id, order["status"])
    return jsonify(order)


@app.route("/orders", methods=["GET"])
def list_orders():
    status = request.args.get("status")
    limit = request.args.get("limit", "50")
    try:
        result = orders.list_orders(status=status, limit=limit)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    log.info("GET /orders 200 count=%d", len(result))
    return jsonify({"orders": result, "count": len(result)})


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


# NOTE: monitoring hits GET /orders?limit=1 as a liveness probe because we
# never got around to a proper health endpoint.


def main():
    setup_logging()
    db.init_db()
    print("OrderBase v%s listening on %s:%s (debug=%s)"
          % (APP_VERSION, HOST, PORT, DEBUG))
    # Reloader off: it double-forks under systemd and the unit flaps.
    app.run(host=HOST, port=PORT, debug=DEBUG, use_reloader=False)


if __name__ == "__main__":
    main()
