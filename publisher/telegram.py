"""
SORCERER — Telegram Publisher
============================
Two modes:

1. ALERT (already in SORCERER) — sends signal briefing to your personal chat
2. CHANNEL BROADCAST — posts finished video + caption to your Telegram channel
3. COMMUNITY POST — posts discussion prompt to a group

No API approval needed. No cost. Works immediately.

Setup for channel posting:
  1. Create a Telegram channel (or use existing)
  2. Add your SORCERER bot as an administrator of the channel
  3. Get the channel username or ID
  4. Add to .env: TELEGRAM_CHANNEL_ID=@yourchannel or -100xxxxxxxxxx

Your bot token is already in .env from SORCERER setup.
"""

import requests
from pathlib import Path

TG_API = "https://api.telegram.org"


def _url(token, method):
    return f"{TG_API}/bot{token}/{method}"


def send_alert(message, token, chat_id, log_fn=print):
    """Send text alert to personal chat (existing SORCERER function)."""
    if not token or not chat_id:
        return False
    try:
        r = requests.post(
            _url(token, "sendMessage"),
            json={
                "chat_id":                  chat_id,
                "text":                     message,
                "parse_mode":               "HTML",
                "disable_web_page_preview": False,
            },
            timeout=10,
        )
        return r.ok
    except Exception:
        return False


def send_video_alert(video_path, caption, token, chat_id, log_fn=print):
    """
    Send the finished video file directly to your personal Telegram chat.
    Great for review before it goes public.
    Max file size: 2GB (Telegram limit).
    """
    if not token or not chat_id:
        return False, "no token/chat"

    if not Path(video_path).exists():
        return False, f"video file not found: {video_path}"

    file_size_mb = Path(video_path).stat().st_size / (1024 * 1024)
    if file_size_mb > 1900:
        log_fn(f"  ⚠️  Video {file_size_mb:.0f}MB exceeds Telegram 2GB limit — sending link only")
        return send_alert(caption, token, chat_id, log_fn), "size_limit"

    try:
        log_fn(f"  📱  Sending video to your Telegram ({file_size_mb:.0f}MB)...")
        with open(video_path, "rb") as f:
            r = requests.post(
                _url(token, "sendVideo"),
                data={
                    "chat_id":    chat_id,
                    "caption":    caption[:1024],
                    "parse_mode": "HTML",
                    "supports_streaming": True,
                },
                files={"video": ("video.mp4", f, "video/mp4")},
                timeout=300,
            )
        if r.ok:
            log_fn("  ✅  Video sent to your Telegram")
            return True, r.json().get("result", {}).get("message_id", "")
        else:
            log_fn(f"  ⚠️  Telegram video send failed: {r.text[:200]}")
            return False, r.text
    except Exception as e:
        log_fn(f"  ❌  Telegram error: {e}")
        return False, str(e)


def broadcast_to_channel(video_path, captions, youtube_url,
                          token, channel_id, log_fn=print):
    """
    Broadcast full video + caption to your Telegram channel.
    If video too large, sends a text post with YouTube link.

    channel_id: @yourchannel or numeric ID like -1001234567890
    """
    if not token or not channel_id:
        log_fn("  ⚠️  No TELEGRAM_CHANNEL_ID — skipping channel broadcast")
        return False, "not configured"

    tg_caps = captions.get("telegram", {})
    post    = tg_caps.get("channel_post", "").replace("[YT_LINK]", youtube_url)
    caption = f"{post}\n\n▶️ <a href='{youtube_url}'>Watch full video →</a>"

    # Try video upload first
    if video_path and Path(video_path).exists():
        file_size_mb = Path(video_path).stat().st_size / (1024 * 1024)

        if file_size_mb <= 1900:
            try:
                log_fn(f"  📢  Broadcasting to Telegram channel ({file_size_mb:.0f}MB)...")
                with open(video_path, "rb") as f:
                    r = requests.post(
                        _url(token, "sendVideo"),
                        data={
                            "chat_id":           channel_id,
                            "caption":           caption[:1024],
                            "parse_mode":        "HTML",
                            "supports_streaming": True,
                        },
                        files={"video": ("video.mp4", f, "video/mp4")},
                        timeout=300,
                    )
                if r.ok:
                    log_fn(f"  ✅  Telegram channel broadcast complete")
                    return True, r.json().get("result", {}).get("message_id", "")
            except Exception as e:
                log_fn(f"  ⚠️  Video broadcast failed ({e}) — sending text post")

    # Fallback: text post with link
    try:
        log_fn("  📢  Sending text post to Telegram channel...")
        r = requests.post(
            _url(token, "sendMessage"),
            json={
                "chat_id":                  channel_id,
                "text":                     caption,
                "parse_mode":               "HTML",
                "disable_web_page_preview": False,
            },
            timeout=15,
        )
        if r.ok:
            log_fn("  ✅  Telegram channel post sent")
            return True, r.json().get("result", {}).get("message_id", "")
        return False, r.text
    except Exception as e:
        log_fn(f"  ❌  Telegram channel post failed: {e}")
        return False, str(e)


def post_to_group(discussion_prompt, youtube_url, token, group_id, log_fn=print):
    """
    Post a discussion prompt to a Telegram group.
    group_id: numeric group/supergroup ID
    """
    if not token or not group_id:
        return False, "not configured"

    tg_caps = {}
    text = f"{discussion_prompt}\n\n▶️ {youtube_url}"

    try:
        r = requests.post(
            _url(token, "sendMessage"),
            json={
                "chat_id":    group_id,
                "text":       text,
                "parse_mode": "HTML",
            },
            timeout=15,
        )
        if r.ok:
            log_fn("  ✅  Telegram group post sent")
            return True, ""
        return False, r.text
    except Exception as e:
        return False, str(e)
