# utils.py -- grab bag of helpers. (TODO: split this up some day. -- J, 2018)

import datetime

VALID_STATUSES = ("NEW", "PAID", "SHIPPED", "CANCELLED")


def format_order_id(n):
    # WMS export parses fixed-width IDs -- do not change the padding.
    # (The warehouse system reads chars 0-7 of each line of the nightly
    # export file. An ID longer or shorter than 8 chars corrupts the batch.)
    return "%08d" % int(n)


def money(x):
    """Round a float to 2 decimal places. Good enough for money. (Is it?)"""
    return round(x, 2)


def format_money(x):
    # Pretty much the same as money() but returns a string. Kept because
    # the old report templates called this one. Don't consolidate blindly.
    return "%.2f" % x


def to_cents(x):
    # 2019: started migrating money math to integer cents, never finished.
    # Nothing calls this.
    return int(x * 100)


def parse_ts(s):
    return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def parse_date(s):
    # Same as parse_ts but date-only. (Yes, this could share code. It's fine.)
    return datetime.datetime.strptime(s, "%Y-%m-%d")


def validate_status(status):
    if status not in VALID_STATUSES:
        raise ValueError("bad status: %s" % status)
    return status


def chunk(seq, size):
    # Was used by the old CSV exporter. The exporter is gone; this stayed.
    out = []
    for i in range(0, len(seq), size):
        out.append(seq[i:i + size])
    return out
