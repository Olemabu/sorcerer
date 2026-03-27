#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════╗
║  SORCERER — Personal YouTube Viral Intelligence Agent       ║
║  Always-on radar. No niche limits. Built for one person.  ║
╚═══════════════════════════════════════════════════════════╝

Commands:
  sorcerer add <channel>     — Add any channel to your radar
  sorcerer remove <channel>  — Stop monitoring a channel
  sorcerer list              — See everything you're watching
  sorcerer scan              — Run a full scan right now
  sorcerer status            — Scan history + alert log
  sorcerer test              — Check setup + preview alert format
  sorcerer daemon            — Run continuously (auto-scans every 2h)
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

try:
    import requests
    from dotenv import load_dotenv
except ImportError:
    print("Run: pip install requests python-dotenv")
    sys.exit(1)

from engine import (
    resolve_channel, fetch_videos, fetch_comments,
    build_baseline, classify,
)
from intelligence import analyse
from alerts import deliver, format_terminal, format_telegram

load_dotenv()

# ── Config ──────────────────────────────────────────────────────────────────
YT_KEY        = os.getenv("YOUTUBE_API_KEY", "")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
TG_TOKEN      = os.getenv("TELEGRAM_TOKEN", "")
TG_CHAT       = os.getenv("TELEGRAM_CHAT_ID", "")

# SCAN_ONLY mode: set to "true" when credits are low.
# Radar still detects all signals and sends Telegram alerts with video data,
# but skips ALL Claude API calls (intelligence, script, director). $0 cost.
SCAN_ONLY = os.getenv("SCAN_ONLY", "false").lower() == "true"

SCAN_INTERVAL_HOURS = int(os.getenv("SCAN_INTERVAL_HOURS", "2"))

BASE_DIR = Path(__file__).parent
# On Railway: mount a volume at /data to persist DB across deploys.
# Locally: falls back to the project directory.
DATA_DIR = Path(os.getenv("SORCERER_DATA_DIR", BASE_DIR))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE  = DATA_DIR / "sorcerer_db.json"
LOG_FILE = DATA_DIR / "sorcerer_log.txt"


# ── DB ──────────────────────────────────────────────────────────────────────
ALERT_EXPIRY_DAYS = 7   # forget alerts older than this — prevents unbounded growth

def load_db():
    if DB_FILE.exists():
        db = json.loads(DB_FILE.read_text())

        # ── Migrate: list → dict with timestamps ──
        # Old format: ["videoId_VIRAL", ...]
        # New format: {"videoId_VIRAL": "2026-03-16T12:00:00", ...}
        if isinstance(db.get("seen_alerts"), list):
            db["seen_alerts"] = {
                key: datetime.now().isoformat()
                for key in db["seen_alerts"]
            }

        # ── Expire old entries ──
        cutoff = datetime.now().timestamp() - (ALERT_EXPIRY_DAYS * 86400)
        db["seen_alerts"] = {
            key: ts for key, ts in db["seen_alerts"].items()
            if datetime.fromisoformat(ts).timestamp() > cutoff
        }

        return db

    return {
        "channels":    {},
        "seen_alerts": {},
        "scans":       0,
        "last_scan":   None,
        "total_alerts": 0,
    }

def save_db(db):
    DB_FILE.write_text(json.dumps(db, indent=2))


# ── Logging ──────────────────────────────────────────────────────────────────
def log(msg):
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def log_plain(msg):
    """For pre-formatted blocks (no timestamp prefix)."""
    print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")


# ── Core scan ────────────────────────────────────────────────────────────────
def run_scan(db, quiet=False):
    if not YT_KEY:
        print("❌  No YOUTUBE_API_KEY in .env — cannot scan")
        return 0

    channels = db.get("channels", {})
    if not channels:
        print("No channels added. Use: sorcerer add <channel>")
        return 0


    if not quiet:
        if SCAN_ONLY:
            intel_status = "SCAN ONLY (no AI — $0 mode)"
        elif ANTHROPIC_KEY:
            intel_status = "ON ✓"
        else:
            intel_status = "OFF (add ANTHROPIC_API_KEY to enable)"
        log(f"SCAN START — {len(channels)} channels — intelligence {intel_status}")

    new_alerts = []

    for cid, ch in channels.items():
        if not quiet:
            print(f"  📡  {ch['title'][:40]}...", end=" ", flush=True)

        try:
            videos, subs = fetch_videos(cid, YT_KEY, max_results=30)

            if not videos:
                if not quiet: print("no videos found")
                continue

            # Update baseline
            baseline = build_baseline(videos)
            if baseline:
                db["channels"][cid]["baseline"] = baseline
            else:
                baseline = ch.get("baseline")

            db["channels"][cid]["subscribers"]  = subs
            db["channels"][cid]["last_checked"] = datetime.now().isoformat()

            if not baseline:
                if not quiet: print(f"building baseline ({len(videos)} videos scraped, need more history)")
                save_db(db)
                continue

            # Check recent videos
            recent = [v for v in videos if v["age_hours"] <= 96]
            found  = 0

            for video in recent:
                signal = classify(video, baseline)
                if not signal:
                    continue

                key = f"{video['id']}_{signal['level']}"
                if key in db["seen_alerts"]:
                    continue

                # NEW SIGNAL — route by tier
                if not quiet: print(f"\n  {signal['emoji']}  SIGNAL DETECTED!")
                log(f"Signal: {signal['level']} — {video['channel_title']}: {video['title'][:60]}")

                # ── Lightweight tiers: WARMING / ACCELERATING ──
                # These are early warnings — no AI calls, no script, no cost.
                # Just a Telegram heads-up so you can watch it manually.
                if signal["level"] in ("WARMING", "ACCELERATING"):
                    if TG_TOKEN and TG_CHAT:
                        from alerts import send_telegram
                        early_msg = (
                            f"{signal['emoji']} <b>{signal['level']} SIGNAL</b>\n\n"
                            f"<b>{video['title']}</b>\n"
                            f"Channel: {video['channel_title']}\n"
                            f"Views: {video['views']:,} in {video['age_hours']:.0f}h\n"
                            f"Pace: {video['views_per_hour']:,.0f} views/hr "
                            f"({signal['multiplier']}× baseline)\n"
                            f"Window: {signal['window']}\n\n"
                            f"<i>Early warning — watching this one. "
                            f"Full package fires if it hits RISING.</i>\n\n"
                            f"<a href='https://youtube.com/watch?v={video['id']}'>Watch →</a>"
                        )
                        send_telegram(early_msg, TG_TOKEN, TG_CHAT)
                    log(f"  → {signal['level']} alert sent (no AI cost)")

                    db["seen_alerts"][key] = datetime.now().isoformat()
                    db["total_alerts"] = db.get("total_alerts", 0) + 1
                    db["channels"][cid]["alert_count"] = ch.get("alert_count", 0) + 1
                    new_alerts.append((video, signal))
                    found += 1
                    continue

                # ── Full tiers: RISING / VIRAL ──

                # SCAN_ONLY mode: send data-only alert, skip all Claude calls ($0)
                if SCAN_ONLY or not ANTHROPIC_KEY:
                    if TG_TOKEN and TG_CHAT:
                        from alerts import send_telegram
                        boost_tag = " 📊 ENGAGEMENT BOOSTED" if signal.get("engagement_boost") else ""
                        scan_msg = (
                            f"{signal['emoji']} <b>{signal['level']} SIGNAL</b>{boost_tag}\n\n"
                            f"<b>{video['title']}</b>\n"
                            f"Channel: {video['channel_title']}\n\n"
                            f"📊 <b>Data</b>\n"
                            f"Views: {video['views']:,} in {video['age_hours']:.0f}h\n"
                            f"Pace: {video['views_per_hour']:,.0f} views/hr "
                            f"({signal['multiplier']}× baseline)\n"
                            f"Likes: {video['likes']:,}\n"
                            f"Comments: {video['comment_count']:,}\n"
                            f"Engagement: {video.get('engagement_rate', 0):.1f}% "
                            f"(channel avg: {baseline.get('median_eng_rate', 0):.1f}%)\n"
                            f"Window: {signal['window']}\n\n"
                            f"<i>SCAN ONLY mode — AI pipeline off. "
                            f"Set SCAN_ONLY=false and top up credits to get full scripts.</i>\n\n"
                            f"<a href='https://youtube.com/watch?v={video['id']}'>Watch →</a>"
                        )
                        send_telegram(scan_msg, TG_TOKEN, TG_CHAT)
                    log(f"  → {signal['level']} alert sent (scan-only, $0)")

                    db["seen_alerts"][key] = datetime.now().isoformat()
                    db["total_alerts"] = db.get("total_alerts", 0) + 1
                    db["channels"][cid]["alert_count"] = ch.get("alert_count", 0) + 1
                    new_alerts.append((video, signal))
                    found += 1
                    continue

                # ── Full AI pipeline ──
                comments = fetch_comments(video["id"], YT_KEY)
                intel    = analyse(video, signal, baseline, comments, ANTHROPIC_KEY)

                # Deliver signal to Telegram
                deliver(
                    video, signal, baseline, intel,
                    TG_TOKEN, TG_CHAT,
                    log_fn=log_plain,
                )

                db["seen_alerts"][key] = datetime.now().isoformat()
                db["total_alerts"] = db.get("total_alerts", 0) + 1
                db["channels"][cid]["alert_count"] = ch.get("alert_count", 0) + 1
                new_alerts.append((video, signal))
                found += 1

            if found == 0 and not quiet:
                best = recent[0] if recent else videos[0]
                mult = round(best["views_per_hour"] / max(baseline["median_vph"], 1), 1)
                print(f"quiet — top: {mult}× baseline")

        except Exception as e:
            if not quiet: print(f"error — {e}")
            log(f"Error scanning {ch.get('title', cid)}: {e}")

        time.sleep(0.4)   # be gentle with the API

    db["scans"]       = db.get("scans", 0) + 1
    db["last_scan"]   = datetime.now().isoformat()
    save_db(db)

    # Google Trends scan
    try:
        from trends import scan_trends
        scan_trends(
            db               = db,
            telegram_token   = TG_TOKEN,
            telegram_chat_id = TG_CHAT,
            seen_alerts      = db["seen_alerts"],
            log_fn           = log,
        )
        save_db(db)
    except Exception as e:
        log(f"Google Trends scan error: {e}")

    if not quiet:
        print(f"\n  {'─' * 50}")
        if new_alerts:
            log(f"SCAN DONE — {len(new_alerts)} new signal(s)")
            for v, s in new_alerts:
                print(f"  {s['emoji']}  {s['level']} — {v['channel_title']}: {v['title'][:50]}")
        else:
            log("SCAN DONE — all quiet")



    return len(new_alerts)


# ── CLI commands ─────────────────────────────────────────────────────────────
def cmd_add(args):
    if not YT_KEY:
        print("❌  No YOUTUBE_API_KEY in .env")
        return

    db    = load_db()
    query = " ".join(args.channel)
    print(f"🔍  Looking up: {query}")

    cid, title, subs = resolve_channel(query, YT_KEY)

    if not cid:
        print(f"❌  Could not find channel: {query}")
        return
    if cid in db["channels"]:
        print(f"✅  Already on radar: {title}")
        return

    db["channels"][cid] = {
        "id":          cid,
        "title":       title,
        "subscribers": subs,
        "added":       datetime.now().isoformat(),
        "baseline":    None,
        "last_checked": None,
        "alert_count": 0,
    }
    save_db(db)
    print(f"✅  Added to radar: {title}  ({subs:,} subs)")
    print(f"    Run 'python sorcerer.py scan' to start")


def cmd_remove(args):
    db    = load_db()
    query = " ".join(args.channel)
    match = next(
        (cid for cid, ch in db["channels"].items()
         if query.lower() in ch["title"].lower() or query == cid),
        None
    )
    if not match:
        print(f"❌  Not found: {query}")
        return
    title = db["channels"][match]["title"]
    del db["channels"][match]
    save_db(db)
    print(f"✅  Removed: {title}")


def cmd_list(args):
    db = load_db()
    if not db["channels"]:
        print("\n  No channels yet. Use: python sorcerer.py add <channel>\n")
        return

    print(f"\n  ╔{'═' * 62}╗")
    print(f"  ║  SORCERER RADAR — {len(db['channels'])} channel(s) monitored{' ' * (43 - len(str(len(db['channels']))))}║")
    print(f"  ╠{'═' * 62}╣")

    for ch in db["channels"].values():
        bl   = ch.get("baseline")
        bstr = f"{bl['median_vph']:>8,.0f} vph baseline" if bl else "  building baseline..."
        last = (ch.get("last_checked") or "never")[:16].replace("T", " ")
        alrt = ch.get("alert_count", 0)
        print(f"  ║  {ch['title'][:34]:<34}  {ch['subscribers']:>9,} subs  ║")
        print(f"  ║  {'':34}  {bstr:<22}  ║")
        print(f"  ║  {'':34}  last: {last}   alerts: {alrt:<3}  ║")
        print(f"  ╠{'─' * 62}╣")

    total = sum(ch.get("alert_count", 0) for ch in db["channels"].values())
    scans = db.get("scans", 0)
    print(f"  ║  Total scans: {scans:<10} Total alerts fired: {total:<20}  ║")
    print(f"  ╚{'═' * 62}╝\n")


def cmd_scan(args):
    db = load_db()
    run_scan(db)


def cmd_status(args):
    db   = load_db()
    last = db.get("last_scan")

    print(f"\n  SORCERER STATUS")
    print(f"  {'─' * 40}")

    if last:
        ago  = datetime.now() - datetime.fromisoformat(last)
        h, m = int(ago.total_seconds() / 3600), int((ago.total_seconds() % 3600) / 60)
        print(f"  Last scan     : {h}h {m}m ago  ({last[:16]})")
    else:
        print(f"  Last scan     : never")

    print(f"  Total scans   : {db.get('scans', 0)}")
    print(f"  Total alerts  : {db.get('total_alerts', 0)}")
    print(f"  Channels      : {len(db.get('channels', {}))}")
    print(f"  Log file      : {LOG_FILE}")
    print(f"  DB file       : {DB_FILE}")

    # Recent alerts from log
    if LOG_FILE.exists():
        lines  = LOG_FILE.read_text().splitlines()
        signal_lines = [l for l in lines if "Signal:" in l][-5:]
        if signal_lines:
            print(f"\n  Recent alerts:")
            for l in signal_lines:
                print(f"    {l.strip()}")
    print()

def cmd_daemon(args):
    """
    Runs forever. Scans every SCAN_INTERVAL_HOURS hours.
    """
    interval_secs = SCAN_INTERVAL_HOURS * 3600

    _intel_str = 'SCAN ONLY ($0)' if SCAN_ONLY else ('ON ✓' if ANTHROPIC_KEY else 'OFF')
    print(f"""
  ╔══════════════════════════════════════════╗
  ║  SORCERER DAEMON — RUNNING               ║
  ║  Scan interval : every {SCAN_INTERVAL_HOURS}h                   ║
  ║  Channels      : {len(load_db().get('channels', {})):<24}║
  ║  Intelligence  : {_intel_str:<24}║
  ║  Telegram      : {'ON ✓' if TG_TOKEN else 'OFF':<24}║
    ╚══════════════════════════════════════════╝
    """)

    # ── Main scan loop ─────────────────────────────────────────────────────────
    while True:
        db = load_db()
        run_scan(db)
        log(f"Next scan in {SCAN_INTERVAL_HOURS}h — sleeping...")
        time.sleep(interval_secs)


def cmd_test(args):
    print(f"""
  ╔══════════════════════════════════════════╗
  ║  SORCERER — SETUP CHECK                    ║
  ╚══════════════════════════════════════════╝
    """)

    checks = [
        ("YouTube API key",   YT_KEY,        "REQUIRED — get free at console.cloud.google.com"),
        ("Anthropic API key", ANTHROPIC_KEY, "Needed for comment analysis + video recommendations"),
        ("Telegram token",    TG_TOKEN,      "Optional — for phone alerts"),
        ("Telegram chat ID",  TG_CHAT,       "Optional — paired with token"),
    ]

    all_good = True
    for label, val, note in checks:
        if val:
            print(f"  ✅  {label:<22} {val[:12]}...")
        else:
            icon = "❌" if "REQUIRED" in note else "⚠️ "
            print(f"  {icon}  {label:<22} NOT SET  ({note})")
            if "REQUIRED" in note:
                all_good = False

    print(f"\n  {'─' * 50}")
    print(f"  Sample alert (what you'll see when a signal fires):\n")

    # Mock data
    mv = {
        "id": "dQw4w9WgXcQ", "title": "OpenAI Just Changed The Game — Nobody Is Ready",
        "channel_title": "TechVision", "age_hours": 7.5,
        "views": 610000, "views_per_hour": 81333,
        "likes": 24000, "comment_count": 5100, "duration_mins": 13,
    }
    mb = {
        "median_vph": 10200, "mean_vph": 11400, "stdev_vph": 2800,
        "median_duration": 11, "sample_size": 19,
    }
    ms = {"level": "VIRAL", "emoji": "🔥", "multiplier": 8.0, "window": "48h"}
    mi = {
        "comment_pulse": (
            "Audience is oscillating between excitement and existential dread — "
            "top comments are people tagging their entire contact list. "
            "The phrase 'nobody saw this coming' is repeating across hundreds of comments."
        ),
        "why_spiking": (
            "Perfect storm: major OpenAI news cycle + a title that implies insiders have "
            "information the public doesn't — manufactured urgency working at full force."
        ),
        "my_video_angle": "\"I Tested Every New OpenAI Feature for 72 Hours — Here's What Will Actually Change Your Life\"",
        "hook_idea": (
            "Open mid-screen recording with your reaction face. "
            "First line: 'I've been testing this for 3 days and I genuinely can't go back.' "
            "No intro. No logo. Straight into the most insane demo."
        ),
        "recommended_length_mins": 21,
        "length_reasoning": "Their 13 min feels rushed — a 21-min deep dive with real testing becomes the definitive video on the topic.",
        "content_structure": [
            "0:00–2:00 — Hook: your raw reaction + the most impressive thing you found. Make them feel like they're missing out.",
            "2:00–9:00 — Feature by feature walkthrough. Real use cases, real results. Not a demo — a verdict.",
            "9:00–16:00 — The part nobody's talking about: second-order effects on jobs, industries, workflows.",
            "16:00–21:00 — Your take. Confident. Opinionated. End with a question that demands a comment.",
        ],
        "worth_pushing_ads": True,
        "ad_reasoning": "Topic will be flooded in 48h — ads now buy you 72h of algorithm momentum before the wave peaks.",
        "target_audience": ["Tech professionals 25–45", "AI curious beginners", "Startup founders"],
        "ad_timing": "6 hours post-upload once organic is confirmed above 10k views/hr",
        "estimated_budget": "$40–80/day for 3 days",
        "urgency_note": "Window is open for roughly 40 hours — after that the topic is saturated and you're late.",
    }

    from alerts import format_terminal
    print(format_terminal(mv, ms, mb, mi))

    if TG_TOKEN and TG_CHAT:
        ans = input("  Send test Telegram message? (y/n): ").strip().lower()
        if ans == "y":
            from alerts import format_telegram, send_telegram
            ok = send_telegram(format_telegram(mv, ms, mb, mi), TG_TOKEN, TG_CHAT)
            print("  ✅  Sent!" if ok else "  ❌  Failed — check token and chat ID")

    if all_good:
        print("  ✅  All good. Run: python sorcerer.py add <channel>  then  python sorcerer.py scan\n")
    else:
        print("  ❌  Missing required keys. Check your .env file.\n")


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        prog="sorcerer",
        description="SORCERER — Personal YouTube Viral Intelligence Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
  Quick start:
    python sorcerer.py add @mkbhd
    python sorcerer.py add "Y Combinator"
    python sorcerer.py add https://youtube.com/@veritasium
    python sorcerer.py scan
    python sorcerer.py daemon        ← runs forever, alerts you on spikes

  Cron (scan every 2h):
    0 */2 * * * cd /path/to/sorcerer && python sorcerer.py scan >> sorcerer_log.txt 2>&1
        """,
    )

    sub = parser.add_subparsers(dest="command")

    p_add = sub.add_parser("add",    help="Add a channel to your radar")
    p_add.add_argument("channel", nargs="+", help="@handle, URL, name, or channel ID")

    p_rm = sub.add_parser("remove", help="Remove a channel from your radar")
    p_rm.add_argument("channel", nargs="+")


    sub.add_parser("list",   help="List all monitored channels")
    sub.add_parser("scan",   help="Run a scan right now")
    sub.add_parser("status", help="Scan history and recent alerts")
    sub.add_parser("daemon", help="Run continuously — auto-scans every 2h")
    sub.add_parser("test",   help="Check your setup and preview the alert format")

    args = parser.parse_args()

    dispatch = {
        "add":    cmd_add,
        "remove": cmd_remove,
        "list":   cmd_list,
        "scan":   cmd_scan,
        "status": cmd_status,
        "daemon": cmd_daemon,
        "test":   cmd_test,
    }

    if args.command in dispatch:
        dispatch[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
