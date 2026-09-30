"""Pure ranked-LP math and constants (no Qt, no I/O, no network).

Extracted from worker.AutoAcceptWorker to satisfy Single Responsibility:
this module can be unit-tested without a League client.
"""

RANKED_QUEUE_ID = 420
RANKED_QUEUE_NAME = "RANKED_SOLO_5x5"

TIERS = (
    "IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "EMERALD",
    "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER",
)
DIVISIONS = ("IV", "III", "II", "I")

STAT_KEYS = ("tier", "division", "lp", "wins", "losses")


def stats_changed(a, b):
    return any((a or {}).get(k) != (b or {}).get(k) for k in STAT_KEYS)


def rank_points(stats):
    tier = (stats or {}).get("tier")
    division = (stats or {}).get("division")
    lp = (stats or {}).get("lp") or 0
    if tier not in TIERS or division not in DIVISIONS:
        return None
    return TIERS.index(tier) * 400 + DIVISIONS.index(division) * 100 + lp


def lp_delta(pre, post):
    if pre is None or post is None:
        return None
    pre_pts = rank_points(pre)
    post_pts = rank_points(post)
    if pre_pts is None or post_pts is None:
        return None
    return post_pts - pre_pts
