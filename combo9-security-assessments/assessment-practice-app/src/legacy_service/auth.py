# auth.py -- bearer-token authentication for OrderBase.
#
# Every caller sends "Authorization: Bearer <token>". Customer and staff
# tokens live, hashed, in the users table; the fulfilment sync uses the
# service token from config.

import functools
import hmac

from flask import g, jsonify, request

from legacy_service import config, db
from legacy_service.utils import hash_token

STAFF = "staff"
CUSTOMER = "customer"

SERVICE_USER = {"id": "svc-wms-sync", "name": "WMS sync", "role": STAFF}


def _bearer_token():
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def user_for_token(token):
    if hmac.compare_digest(token.encode("utf-8"),
                           config.WMS_SYNC_TOKEN.encode("utf-8")):
        return dict(SERVICE_USER)
    rows = db.query(
        "SELECT id, name, role FROM %s WHERE token_sha256 = ?" % db.USERS_TABLE,
        (hash_token(token),))
    if not rows:
        return None
    return dict(rows[0])


def is_staff(user):
    return user["role"] == STAFF


def can_access_order(user, order):
    # Staff see every order; customers see only their own.
    return is_staff(user) or order["owner_id"] == user["id"]


def require_auth(view):
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        token = _bearer_token()
        user = user_for_token(token) if token else None
        if user is None:
            return jsonify({"error": "authentication required"}), 401
        g.user = user
        return view(*args, **kwargs)
    return wrapper
