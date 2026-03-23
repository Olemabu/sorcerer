"""
SORCERER — Master Publisher
==========================
Orchestrates publishing to all platforms with correct
aspect ratios, clip lengths, and captions per platform.

Routing logic:
  Master video (16:9, full length)
    → YouTube      full video
    → Facebook     full video (feed)
    → Telegram     full video (channel) + personal alert

  Vertical clip (9:16, 60-90 sec)
    → Facebook     Reels
    → TikTok       short clip

  Landscape clip (16:9, 60-90 sec)
    → Twitter/X    thread + thumbnail  (Basic tier)
                   native video        (Pro tier)

Each platform gets its own Claude-generated caption.
"""

import os
from pathlib import Path
from datetime import datetime


def publish_all(
    master_video_path,
    clips,
    captions,
    youtube_url,
    config,
    youtube_preset="main",
    log_fn=print,
):
    """
    Publish to all enabled platforms.

    Args:
        master_video_path : path to 16:9 full-length video
        clips             : dict from clipper.prepare_all_clips()
                            keys: clip_vertical, clip_landscape
        captions          : dict from captions.generate_captions()
        youtube_url       : YouTube video URL (from youtube.upload)
        config            : dict of platform toggles + credentials
        youtube_preset    : name of the YouTube preset to upload to (e.g. 'gaming')
        log_fn            : logging function

    config keys:
        youtube_enabled, facebook_enabled, tiktok_enabled,
        twitter_enabled, telegram_enabled,
        youtube_token_file,
        facebook_page_id, facebook_page_token,
        tiktok_access_token, tiktok_open_id,
        twitter_api_key, twitter_api_secret,
        twitter_access_token, twitter_access_secret,
        telegram_token, telegram_chat_id,
        telegram_channel_id, telegram_group_id,
    """

    results = {}
    clip_v  = clips.get("clip_vertical")
    clip_l  = clips.get("clip_landscape")

    # ── YouTube ────────────────────────────────────────────────────
    
    # Check if a custom preset token exists, otherwise fall back to the default or config
    preset_token = f"yt_token_{youtube_preset}.json"
    if os.path.exists(preset_token):
        token_to_use = preset_token
    else:
        token_to_use = config.get("youtube_token_file", "yt_token.json")
        
    # We enable YouTube publishing if ANY token file is present
    youtube_enabled = config.get("youtube_enabled") or os.path.exists(token_to_use)

    if youtube_enabled and master_video_path:
        log_fn(f"\n  ▶  YOUTUBE (Channel Preset: {youtube_preset})")
        from publisher.youtube import upload as yt_upload
        ok, result = yt_upload(
            video_path  = master_video_path,
            captions    = captions,
            script      = None,
            token_file  = token_to_use,
            log_fn      = log_fn,
        )
        results["youtube"] = {"ok": ok, "result": result}
        if ok:
            youtube_url = f"https://youtube.com/watch?v={result}"

    # ── Facebook Feed ──────────────────────────────────────────────
    if config.get("facebook_enabled") and master_video_path:
        log_fn("\n  ▶  FACEBOOK FEED")
        from publisher.facebook import upload_feed_video
        ok, result = upload_feed_video(
            video_path  = master_video_path,
            captions    = captions,
            page_id     = config.get("facebook_page_id", ""),
            page_token  = config.get("facebook_page_token", ""),
            log_fn      = log_fn,
        )
        results["facebook_feed"] = {"ok": ok, "result": result}

    # ── Facebook Reels ─────────────────────────────────────────────
    if config.get("facebook_enabled") and clip_v:
        log_fn("\n  ▶  FACEBOOK REELS")
        from publisher.facebook import upload_reel
        ok, result = upload_reel(
            clip_path   = clip_v,
            captions    = captions,
            page_id     = config.get("facebook_page_id", ""),
            page_token  = config.get("facebook_page_token", ""),
            log_fn      = log_fn,
        )
        results["facebook_reels"] = {"ok": ok, "result": result}

    # ── TikTok ────────────────────────────────────────────────────
    if config.get("tiktok_enabled") and clip_v:
        log_fn("\n  ▶  TIKTOK")
        from publisher.tiktok import upload as tt_upload
        ok, result = tt_upload(
            clip_path    = clip_v,
            captions     = captions,
            access_token = config.get("tiktok_access_token", ""),
            open_id      = config.get("tiktok_open_id", ""),
            log_fn       = log_fn,
        )
        results["tiktok"] = {"ok": ok, "result": result}

    # ── Twitter/X ─────────────────────────────────────────────────
    if config.get("twitter_enabled"):
        log_fn("\n  ▶  TWITTER/X")
        from publisher.twitter import post_thread, post_video_tweet

        if clip_l and config.get("twitter_pro_tier"):
            ok, result = post_video_tweet(
                clip_path     = clip_l,
                captions      = captions,
                youtube_url   = youtube_url,
                api_key       = config.get("twitter_api_key", ""),
                api_secret    = config.get("twitter_api_secret", ""),
                access_token  = config.get("twitter_access_token", ""),
                access_secret = config.get("twitter_access_secret", ""),
                log_fn        = log_fn,
            )
        else:
            ok, result = post_thread(
                captions      = captions,
                thumbnail_path= None,
                youtube_url   = youtube_url,
                api_key       = config.get("twitter_api_key", ""),
                api_secret    = config.get("twitter_api_secret", ""),
                access_token  = config.get("twitter_access_token", ""),
                access_secret = config.get("twitter_access_secret", ""),
                log_fn        = log_fn,
            )
        results["twitter"] = {"ok": ok, "result": result}

    # ── Telegram ──────────────────────────────────────────────────
    if config.get("telegram_enabled"):
        token    = config.get("telegram_token", "")
        chat_id  = config.get("telegram_chat_id", "")
        chan_id  = config.get("telegram_channel_id", "")
        group_id = config.get("telegram_group_id", "")

        from publisher.telegram import (
            broadcast_to_channel, post_to_group, send_video_alert
        )
        tg_caps = captions.get("telegram", {})

        # Personal alert with video
        if chat_id and master_video_path:
            log_fn("\n  ▶  TELEGRAM PERSONAL ALERT")
            ok, result = send_video_alert(
                video_path = master_video_path,
                caption    = f"✅ New video ready!\n\n{youtube_url}",
                token      = token,
                chat_id    = chat_id,
                log_fn     = log_fn,
            )
            results["telegram_alert"] = {"ok": ok, "result": result}

        # Channel broadcast
        if chan_id:
            log_fn("\n  ▶  TELEGRAM CHANNEL")
            ok, result = broadcast_to_channel(
                video_path   = master_video_path,
                captions     = captions,
                youtube_url  = youtube_url,
                token        = token,
                channel_id   = chan_id,
                log_fn       = log_fn,
            )
            results["telegram_channel"] = {"ok": ok, "result": result}

        # Group discussion post
        if group_id:
            log_fn("\n  ▶  TELEGRAM GROUP")
            prompt = tg_caps.get("community_prompt", "What do you think?")
            from publisher.telegram import post_to_group
            ok, result = post_to_group(prompt, youtube_url, token, group_id, log_fn)
            results["telegram_group"] = {"ok": ok, "result": result}

    # ── Summary ────────────────────────────────────────────────────
    log_fn("\n" + "═" * 56)
    log_fn("  📊  PUBLISH SUMMARY")
    log_fn("─" * 56)

    ok_count   = sum(1 for v in results.values() if v.get("ok"))
    fail_count = sum(1 for v in results.values() if not v.get("ok"))

    platform_names = {
        "youtube":          "YouTube",
        "facebook_feed":    "Facebook Feed",
        "facebook_reels":   "Facebook Reels",
        "tiktok":           "TikTok",
        "twitter":          "Twitter/X",
        "telegram_alert":   "Telegram (personal)",
        "telegram_channel": "Telegram (channel)",
        "telegram_group":   "Telegram (group)",
    }

    for key, val in results.items():
        name   = platform_names.get(key, key)
        status = "✅" if val["ok"] else "❌"
        log_fn(f"  {status}  {name}")

    log_fn("─" * 56)
    log_fn(f"  {ok_count} published · {fail_count} failed")
    log_fn("═" * 56 + "\n")

    return results


def build_config_from_env():
    """Build publisher config dict from environment variables."""
    import os
    return {
        # Platform toggles
        "youtube_enabled":   bool(os.getenv("YOUTUBE_TOKEN_FILE")),
        "facebook_enabled":  bool(os.getenv("FACEBOOK_PAGE_TOKEN")),
        "tiktok_enabled":    bool(os.getenv("TIKTOK_ACCESS_TOKEN")),
        "twitter_enabled":   bool(os.getenv("TWITTER_API_KEY")),
        "telegram_enabled":  bool(os.getenv("TELEGRAM_TOKEN")),

        # YouTube
        "youtube_token_file":    os.getenv("YOUTUBE_TOKEN_FILE", "yt_token.json"),

        # Facebook
        "facebook_page_id":    os.getenv("FACEBOOK_PAGE_ID", ""),
        "facebook_page_token": os.getenv("FACEBOOK_PAGE_TOKEN", ""),

        # TikTok
        "tiktok_access_token": os.getenv("TIKTOK_ACCESS_TOKEN", ""),
        "tiktok_open_id":      os.getenv("TIKTOK_OPEN_ID", ""),

        # Twitter
        "twitter_api_key":      os.getenv("TWITTER_API_KEY", ""),
        "twitter_api_secret":   os.getenv("TWITTER_API_SECRET", ""),
        "twitter_access_token": os.getenv("TWITTER_ACCESS_TOKEN", ""),
        "twitter_access_secret":os.getenv("TWITTER_ACCESS_SECRET", ""),
        "twitter_pro_tier":     os.getenv("TWITTER_PRO_TIER", "").lower() == "true",

        # Telegram
        "telegram_token":      os.getenv("TELEGRAM_TOKEN", ""),
        "telegram_chat_id":    os.getenv("TELEGRAM_CHAT_ID", ""),
        "telegram_channel_id": os.getenv("TELEGRAM_CHANNEL_ID", ""),
        "telegram_group_id":   os.getenv("TELEGRAM_GROUP_ID", ""),
    }
