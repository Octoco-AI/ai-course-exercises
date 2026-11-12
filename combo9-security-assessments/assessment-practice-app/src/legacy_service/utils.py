# utils.py -- grab bag of helpers. (TODO: split this up some day.)

import datetime
import hashlib

VALID_STATUSES = ("NEW", "PAID", "SHIPPED", "CANCELLED")


def format_order_id(n):
    # WMS export parses fixed-width IDs -- do not change the padding.
    # (The warehouse system reads chars 0-7 of each line of the nightly
    # export file. An ID longer or shorter than 8 chars corrupts the batch.)
    return "%08d" % int(n)


def normalise_order_id(raw):
    # Accept bare numeric ids ("42") as a convenience and pad them, using the
    # same width as format_order_id.
    if raw.isdigit() and len(raw) < 8:
        return raw.rjust(8, "0")
    return raw


def money(x):
    """Round a float to 2 decimal places."""
    return round(x, 2)


def parse_ts(s):
    return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def parse_date(s):
    return datetime.datetime.strptime(s, "%Y-%m-%d")


def validate_status(status):
    if status not in VALID_STATUSES:
        raise ValueError("bad status: %s" % status)
    return status


def hash_token(token):
    # API tokens are stored as SHA-256 digests, never in the clear.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
