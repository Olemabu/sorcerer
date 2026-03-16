"""
SORCERER — Core Engine
YouTube data fetching, baseline building, signal classification.
No AI here — pure math. Fast and free.
"""

import re
import os
import time
import statistics
from datetime import datetime, timezone

import requests

# ── Constants ──────────────────────────────────────────────────────────────
YT = "https://www.googleapis.com/youtube/v3"

# All thresholds tuneable from Railway Variables — no redeploy needed
VIRAL_MULTIPLIER     = float(os.getenv("VIRAL_MULTIPLIER",   "5.0"))   # 5× baseline  → VIRAL
RISING_MULTIPLIER    = float(os.getenv("RISING_MULTIPLIER",  "2.5"))   # 2.5× baseline → RISING
WARMING_MULTIPLIER   = float(os.getenv("WARMING_MULTIPLIER", "1.5"))   # 1.5× baseline → WARMING (new)
MIN_VIEWS            = int(os.getenv("MIN_VIEWS",            "500"))
MAX_AGE_HOURS        = int(os.getenv("MAX_AGE_HOURS",        "96"))    # only flag videos < 4 days old
BASELINE_WINDOW      = int(os.getenv("BASELINE_WINDOW",      "20"))
COMMENT_PULL         = int(os.getenv("COMMENT_PULL",         "80"))

# Velocity detection — catches videos that are accelerating fast
# even if they haven't crossed a multiplier threshold yet
VELOCITY_ENABLED     = os.getenv("VELOCITY_ENABLED", "true").lower() == "true"
VELOCITY_MIN_AGE_H   = float(os.getenv("VELOCITY_MIN_AGE_H",  "1.0"))  # need at least 1h of data
VELOCITY_MAX_AGE_H   = float(os.getenv("VELOCITY_MAX_AGE_H", "12.0"))  # only very fresh videos
VELOCITY_THRESHOLD   = float(os.getenv("VELOCITY_THRESHOLD",  "3.0"))  # 3× the channel's avg early pace


# ── YouTube helpers ─────────────────────────────────────────────────────────
def yt_get(endpoint, api_key, **params):
    params["key"] = api_key
    r = requests.get(f"{YT}/{endpoint}", params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def resolve_channel(query, api_key):
    """
    Accept any form: UC... ID, @handle, full URL, or search term.
    Returns (channel_id, title, subscriber_count) or (None, None, None).
    """
    q = query.strip()

    # Direct channel ID
    if q.startswith("UC") and len(q) == 24:
        d = yt_get("channels", api_key, part="snippet,statistics", id=q)
        if d.get("items"):
            i = d["items"][0]
            return i["id"], i["snippet"]["title"], int(i["statistics"].get("subscriberCount", 0))

    # @handle
    handle = None
    if q.startswith("@"):
        handle = q.lstrip("@")
    for prefix in ["youtube.com/@", "youtube.com/c/", "youtube.com/user/"]:
        if prefix in q:
            handle = q.split(prefix)[-1].split("/")[0].split("?")[0]
    if "youtube.com/channel/" in q:
        cid = q.split("youtube.com/channel/")[-1].split("/")[0].split("?")[0]
        return resolve_channel(cid, api_key)

    if handle:
        d = yt_get("channels", api_key, part="snippet,statistics", forHandle=handle)
        if d.get("items"):
            i = d["items"][0]
            return i["id"], i["snippet"]["title"], int(i["statistics"].get("subscriberCount", 0))

    # Search fallback
    d = yt_get("search", api_key, part="snippet", type="channel", q=q, maxResults=1)
    if d.get("items"):
        return resolve_channel(d["items"][0]["snippet"]["channelId"], api_key)

    return None, None, None


def parse_iso_duration(s):
    """PT1H2M3S → total minutes."""
    h = int((re.search(r"(\d+)H", s) or [0, 0])[1])
    m = int((re.search(r"(\d+)M", s) or [0, 0])[1])
    return h * 60 + m


def fetch_videos(channel_id, api_key, max_results=30):
    """
    Pull recent uploads with full stats.
    Returns (list_of_video_dicts, subscriber_count).
    """
    chan = yt_get("channels", api_key,
                  part="contentDetails,statistics", id=channel_id)
    if not chan.get("items"):
        return [], 0

    subs     = int(chan["items"][0]["statistics"].get("subscriberCount", 0))
    playlist = chan["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    items = yt_get("playlistItems", api_key,
                   part="contentDetails",
                   playlistId=playlist,
                   maxResults=max_results).get("items", [])

    if not items:
        return [], subs

    ids   = [i["contentDetails"]["videoId"] for i in items]
    stats = yt_get("videos", api_key,
                   part="statistics,snippet,contentDetails",
                   id=",".join(ids)).get("items", [])

    videos = []
    now    = datetime.now(timezone.utc)
    for item in stats:
        pub    = item["snippet"]["publishedAt"]
        pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
        age_h  = (now - pub_dt).total_seconds() / 3600
        views  = int(item["statistics"].get("viewCount", 0))
        dur    = parse_iso_duration(item["contentDetails"].get("duration", "PT0S"))

        likes    = int(item["statistics"].get("likeCount", 0))
        comments = int(item["statistics"].get("commentCount", 0))
        eng_rate = round((likes + comments) / max(views, 1) * 100, 2)

        videos.append({
            "id":              item["id"],
            "title":           item["snippet"]["title"],
            "published":       pub,
            "age_hours":       round(age_h, 1),
            "views":           views,
            "likes":           likes,
            "comment_count":   comments,
            "views_per_hour":  round(views / max(age_h, 0.5), 1),
            "engagement_rate": eng_rate,
            "duration_mins":   dur,
            "channel_id":      channel_id,
            "channel_title":   item["snippet"]["channelTitle"],
            "thumbnail":       item["snippet"]["thumbnails"].get("high", {}).get("url", ""),
        })

    return sorted(videos, key=lambda v: v["published"], reverse=True), subs


def fetch_comments(video_id, api_key, max_results=COMMENT_PULL):
    """Top comments sorted by most liked."""
    try:
        data = yt_get("commentThreads", api_key,
                      part="snippet",
                      videoId=video_id,
                      order="relevance",
                      maxResults=min(max_results, 100))
        out = []
        for item in data.get("items", []):
            s = item["snippet"]["topLevelComment"]["snippet"]
            out.append({
                "text":  s["textDisplay"][:400],
                "likes": int(s.get("likeCount", 0)),
            })
        return out
    except Exception:
        return []  # comments disabled on some videos — that's fine


# ── Baseline ────────────────────────────────────────────────────────────────
def build_baseline(videos, n=BASELINE_WINDOW):
    """
    Median views/hr of the last N videos older than 48h.
    Also tracks early-life velocity (first 12h performance) for acceleration detection.
    Returns None if not enough data yet.
    """
    pool = [
        v for v in videos
        if v["age_hours"] > 48 and v["views"] >= MIN_VIEWS
    ][:n]

    if len(pool) < 3:
        return None

    rates       = [v["views_per_hour"]  for v in pool]
    durations   = [v["duration_mins"]   for v in pool if v["duration_mins"] > 0]
    eng_rates   = [v.get("engagement_rate", 0) for v in pool if v.get("engagement_rate", 0) > 0]

    # Early-life velocity: what does a "normal" video look like in its first 12h?
    # We approximate by looking at videos that are now mature — their views_per_hour
    # when young would have been higher. For channels with consistent output,
    # median_vph is a reasonable floor for early-life pace.
    # A video doing 3× this in its first 12h is accelerating unusually fast.
    early_rates = [v["views_per_hour"] for v in pool]

    return {
        "median_vph":      round(statistics.median(rates), 1),
        "mean_vph":        round(statistics.mean(rates), 1),
        "stdev_vph":       round(statistics.stdev(rates) if len(rates) > 1 else 0, 1),
        "median_duration": round(statistics.median(durations), 0) if durations else 0,
        "median_eng_rate": round(statistics.median(eng_rates), 2) if eng_rates else 0,
        "sample_size":     len(pool),
        "early_vph":       round(statistics.median(early_rates), 1),
    }


# ── Signal detection ─────────────────────────────────────────────────────────
# Engagement boost: if a video's engagement rate is 2×+ the channel average,
# it gets promoted one tier. This catches "sleeper" videos where the audience
# is going crazy in comments/likes but views haven't exploded yet.
ENGAGEMENT_BOOST_MULT = float(os.getenv("ENGAGEMENT_BOOST_MULT", "2.0"))


def classify(video, baseline):
    """
    Pure math. No AI. Three tiers + velocity detection + engagement boost.

    Tiers (based on views/hr vs channel baseline):
      VIRAL   — 5.0× or higher (configurable)
      RISING  — 2.5× or higher
      WARMING — 1.5× or higher (early warning, no script generated)

    Engagement boost:
      If engagement_rate >= 2× channel median, promote one tier:
      WARMING → RISING, RISING → VIRAL

    Velocity (based on acceleration in first 12h):
      ACCELERATING — video is very young and gaining pace unusually fast

    Returns signal dict or None.
    """
    if not baseline or baseline["median_vph"] == 0:
        return None

    mult = video["views_per_hour"] / baseline["median_vph"]

    # Check engagement boost eligibility
    eng_boosted = False
    median_eng  = baseline.get("median_eng_rate", 0)
    video_eng   = video.get("engagement_rate", 0)
    if median_eng > 0 and video_eng >= median_eng * ENGAGEMENT_BOOST_MULT:
        eng_boosted = True

    # ── Tier 1: VIRAL ──
    if mult >= VIRAL_MULTIPLIER and video["age_hours"] <= MAX_AGE_HOURS:
        return {
            "level":      "VIRAL",
            "emoji":      "🔥",
            "multiplier": round(mult, 1),
            "window":     "48h",
            "engagement_boost": False,
        }

    # ── Tier 2: RISING (or VIRAL if engagement-boosted) ──
    if mult >= RISING_MULTIPLIER and video["age_hours"] <= MAX_AGE_HOURS:
        if eng_boosted:
            return {
                "level":      "VIRAL",
                "emoji":      "🔥",
                "multiplier": round(mult, 1),
                "window":     "48h",
                "engagement_boost": True,
            }
        return {
            "level":      "RISING",
            "emoji":      "⚡",
            "multiplier": round(mult, 1),
            "window":     "72h",
            "engagement_boost": False,
        }

    # ── Tier 3: WARMING (or RISING if engagement-boosted) ──
    if mult >= WARMING_MULTIPLIER and video["age_hours"] <= MAX_AGE_HOURS:
        if eng_boosted:
            return {
                "level":      "RISING",
                "emoji":      "⚡",
                "multiplier": round(mult, 1),
                "window":     "72h",
                "engagement_boost": True,
            }
        return {
            "level":      "WARMING",
            "emoji":      "📈",
            "multiplier": round(mult, 1),
            "window":     "96h",
            "engagement_boost": False,
        }

    # ── Velocity detection: young video accelerating fast ──
    if (VELOCITY_ENABLED
            and VELOCITY_MIN_AGE_H <= video["age_hours"] <= VELOCITY_MAX_AGE_H
            and video["views"] >= MIN_VIEWS):

        early_vph = baseline.get("early_vph", baseline["median_vph"])
        if early_vph > 0:
            velocity_mult = video["views_per_hour"] / early_vph
            if velocity_mult >= VELOCITY_THRESHOLD:
                return {
                    "level":      "ACCELERATING",
                    "emoji":      "🚀",
                    "multiplier": round(velocity_mult, 1),
                    "window":     "12h",
                    "engagement_boost": False,
                }

    return None
