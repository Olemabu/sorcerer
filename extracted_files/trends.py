"""
SORCERER — Google Trends Monitor
==================================
Catches waves 24-48 hours before they hit YouTube.
This is your early warning system.

No API key needed. No cost. Completely free.
Uses the unofficial Google Trends API via pytrends.

What it does:
  - Monitors keywords related to your watched channels
  - Detects search interest spikes in real time
  - Cross-references with YouTube signals for stronger alerts
  - Fires early warning alerts before competitors even notice

Install: pip install pytrends
"""

import time
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False


# ── Config ────────────────────────────────────────────────────────────────────
SPIKE_THRESHOLD    = 80    # Interest score 0-100. 80+ = significant spike
RISING_THRESHOLD   = 50    # 50+ = worth watching
MAX_KEYWORDS       = 5     # Google Trends max per request
TIMEFRAME          = "now 1-d"   # Last 24 hours
GEO                = ""          # Worldwide. Set to "US" for US only


# ── Trend checker ─────────────────────────────────────────────────────────────
def check_trends(keywords, geo=GEO, log_fn=print):
    """
    Check Google Trends for a list of keywords.
    Returns list of signals with interest scores.

    keywords: list of strings to check
    geo: country code or "" for worldwide
    """
    if not PYTRENDS_AVAILABLE:
        log_fn("  ⚠ pytrends not installed — run: pip install pytrends")
        return []

    if not keywords:
        return []

    signals = []

    # Process in batches of 5 (Google Trends limit)
    for i in range(0, len(keywords), MAX_KEYWORDS):
        batch = keywords[i:i + MAX_KEYWORDS]

        try:
            pt = TrendReq(hl="en-US", tz=0, timeout=(10, 25))
            pt.build_payload(batch, timeframe=TIMEFRAME, geo=geo)
            data = pt.interest_over_time()

            if data.empty:
                continue

            for keyword in batch:
                if keyword not in data.columns:
                    continue

                series      = data[keyword]
                current     = int(series.iloc[-1])
                peak_24h    = int(series.max())
                avg_24h     = float(series.mean())

                # Calculate spike vs average
                spike_ratio = round(current / max(avg_24h, 1), 1)

                if current >= SPIKE_THRESHOLD:
                    signals.append({
                        "keyword":     keyword,
                        "level":       "TRENDING",
                        "emoji":       "📈",
                        "score":       current,
                        "peak_24h":    peak_24h,
                        "avg_24h":     round(avg_24h, 1),
                        "spike_ratio": spike_ratio,
                        "source":      "google_trends",
                        "geo":         geo or "worldwide",
                        "timestamp":   datetime.now().isoformat(),
                    })
                elif current >= RISING_THRESHOLD:
                    signals.append({
                        "keyword":     keyword,
                        "level":       "RISING",
                        "emoji":       "📊",
                        "score":       current,
                        "peak_24h":    peak_24h,
                        "avg_24h":     round(avg_24h, 1),
                        "spike_ratio": spike_ratio,
                        "source":      "google_trends",
                        "geo":         geo or "worldwide",
                        "timestamp":   datetime.now().isoformat(),
                    })

            time.sleep(1)  # Be gentle with Google

        except Exception as e:
            log_fn(f"  ⚠ Trends error for {batch}: {e}")
            time.sleep(5)
            continue

    return signals


def get_related_queries(keyword, log_fn=print):
    """
    Get rising related queries for a keyword.
    These are the next wave of topics about to break.
    """
    if not PYTRENDS_AVAILABLE:
        return []

    try:
        pt = TrendReq(hl="en-US", tz=0, timeout=(10, 25))
        pt.build_payload([keyword], timeframe="now 7-d")
        related = pt.related_queries()

        rising = related.get(keyword, {}).get("rising")
        if rising is not None and not rising.empty:
            return rising["query"].tolist()[:10]
        return []

    except Exception as e:
        log_fn(f"  ⚠ Related queries error: {e}")
        return []


# ── Extract keywords from channel data ────────────────────────────────────────
def extract_keywords_from_channels(channels_db, log_fn=print):
    """
    Pull relevant search keywords from the channels being monitored.
    Uses channel titles and recent video titles to build keyword list.
    """
    keywords = set()

    for ch in channels_db.values():
        title = ch.get("title", "")

        # Clean channel name into search keywords
        # Remove common words
        stops = {"the", "a", "an", "and", "or", "of", "in", "on", "at",
                 "to", "for", "is", "are", "was", "were", "be", "been",
                 "channel", "official", "tv", "show", "podcast", "clips"}

        words = [w.lower() for w in title.split() if w.lower() not in stops and len(w) > 2]
        if words:
            # Add the full channel topic as a keyword
            keywords.add(" ".join(words[:3]))

    return list(keywords)[:20]  # Max 20 keywords per scan


def add_manual_keywords(db_file, new_keywords):
    """
    Let user add specific keywords to track via Telegram /watch command.
    Stored in the database.
    """
    db_path = Path(db_file)
    if db_path.exists():
        db = json.loads(db_path.read_text())
    else:
        db = {}

    existing = db.get("trend_keywords", [])
    for kw in new_keywords:
        if kw not in existing:
            existing.append(kw.lower().strip())

    db["trend_keywords"] = existing[:50]  # Cap at 50
    db_path.write_text(json.dumps(db, indent=2))
    return existing


def get_manual_keywords(db_file):
    """Get user-defined keywords from database."""
    db_path = Path(db_file)
    if db_path.exists():
        db = json.loads(db_path.read_text())
        return db.get("trend_keywords", [])
    return []


# ── Format trend alert ─────────────────────────────────────────────────────────
def format_trend_alert_telegram(signal):
    """Format a Google Trends signal for Telegram."""
    bars = "█" * min(int(signal["score"] / 10), 10)
    return (
        f"{signal['emoji']} <b>GOOGLE TRENDS — {signal['level']}</b>\n\n"
        f"Keyword: <b>{signal['keyword']}</b>\n"
        f"Interest score: <b>{signal['score']}/100</b>\n"
        f"Momentum: {bars}\n"
        f"24h peak: {signal['peak_24h']}\n"
        f"Spike: {signal['spike_ratio']}× above average\n"
        f"Region: {signal['geo']}\n\n"
        f"⏰ <i>This is 24-48h ahead of YouTube — act now.</i>"
    )


def format_trend_alert_terminal(signal):
    """Format a Google Trends signal for terminal."""
    bars = "█" * min(int(signal["score"] / 10), 10)
    return (
        f"\n  {signal['emoji']}  GOOGLE TRENDS — {signal['level']}\n"
        f"  {'─' * 50}\n"
        f"  Keyword  : {signal['keyword']}\n"
        f"  Score    : {signal['score']}/100\n"
        f"  Momentum : {bars}\n"
        f"  Spike    : {signal['spike_ratio']}× above 24h average\n"
        f"  Region   : {signal['geo'] or 'worldwide'}\n"
        f"  ⏰ 24-48h ahead of YouTube — early mover advantage\n"
        f"  {'─' * 50}\n"
    )


# ── Full trends scan ──────────────────────────────────────────────────────────
def scan_trends(db, telegram_token, telegram_chat_id, seen_alerts, log_fn=print):
    """
    Full Google Trends scan.
    Called from the main daemon scan loop.

    Returns list of new trend signals.
    """
    if not PYTRENDS_AVAILABLE:
        return []

    channels  = db.get("channels", {})
    manual_kw = db.get("trend_keywords", [])

    # Build keyword list from channels + manual additions
    auto_kw   = extract_keywords_from_channels(channels, log_fn)
    all_kw    = list(set(auto_kw + manual_kw))

    if not all_kw:
        log_fn("  📈 Google Trends: no keywords to check yet")
        return []

    log_fn(f"  📈 Google Trends: checking {len(all_kw)} keywords...")
    signals = check_trends(all_kw, log_fn=log_fn)

    new_signals = []
    for signal in signals:
        alert_key = f"trends_{signal['keyword']}_{signal['level']}"

        if alert_key in seen_alerts:
            continue

        # Log to terminal
        log_fn(format_trend_alert_terminal(signal))

        # Send Telegram alert
        if telegram_token and telegram_chat_id:
            try:
                requests.post(
                    f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                    json={
                        "chat_id":    telegram_chat_id,
                        "text":       format_trend_alert_telegram(signal),
                        "parse_mode": "HTML",
                    },
                    timeout=10,
                )
            except Exception:
                pass

        seen_alerts.append(alert_key)
        new_signals.append(signal)

    if not new_signals:
        log_fn(f"  📈 Google Trends: quiet — no spikes detected")

    return new_signals
