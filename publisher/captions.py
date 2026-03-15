"""
SORCERER — Caption Generator
===========================
Claude writes platform-native captions, descriptions,
hashtags and thread copy for every platform.

Each platform has its own language, character limits,
hashtag culture, and audience expectation.
This module handles all of it in one Claude call.
"""

import json
import requests

CLAUDE_MODEL  = "claude-sonnet-4-6"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


def generate_captions(video_title, script, intel, signal, anthropic_key):
    """
    Generate platform-native copy for all 5 platforms in one call.

    Args:
        video_title  : final video title
        script       : full script dict from scriptwriter
        intel        : briefing dict from intelligence layer
        signal       : signal dict (level, multiplier, window)
        anthropic_key: Anthropic API key

    Returns:
        dict with captions for each platform, or fallback defaults
    """
    if not anthropic_key:
        return _fallback_captions(video_title)

    hook       = ""
    cta        = script.get("cta_script", "") if script else ""
    pain_map   = script.get("pain_profit_map", []) if script else []
    seo_tags   = script.get("seo_tags", []) if script else []
    comment_pulse = intel.get("comment_pulse", "") if intel else ""
    why_spiking   = intel.get("why_spiking", "") if intel else ""

    # Pull hook from first script section
    sections = script.get("sections", []) if script else []
    if sections:
        hook = sections[0].get("script", "")[:300]

    pain_block = ""
    for item in pain_map[:2]:
        pain_block += f"Pain: {item.get('pain','')}\nProfit: {item.get('profit','')}\n"

    prompt = f"""You are a social media strategist who writes platform-native copy that actually performs.
You understand the culture, algorithm, and audience of each platform intimately.

VIDEO CONTEXT:
Title        : {video_title}
Signal level : {signal.get('level','VIRAL')} — {signal.get('multiplier',5)}× above competitor baseline
Hook opening : {hook}
Why it's hot : {why_spiking}
Audience feel: {comment_pulse}
SEO tags     : {', '.join(seo_tags[:8])}

PAIN → PROFIT:
{pain_block}

Write platform-native copy for all 5 platforms. Each one should feel written BY a human FOR that platform.
Return ONLY valid JSON. No markdown. No text outside the JSON.

{{
  "youtube": {{
    "title": "Final optimised YouTube title (under 70 chars, searchable, punchy)",
    "description": "Full YouTube description. 180-220 words. First 2 lines are the hook before 'Show more'. Include timestamps as placeholders (00:00 Intro, etc.), 3 relevant links as placeholders, and a subscribe CTA. SEO-optimised but reads human.",
    "tags": ["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10"],
    "end_screen_suggestion": "What to put on the end screen card — which type of video to recommend next"
  }},

  "facebook_feed": {{
    "caption": "Facebook feed post caption. 80-120 words. Conversational. Starts with a question or bold statement. Builds curiosity. Ends with a question to drive comments. Max 3 hashtags — Facebook penalises hashtag stuffing.",
    "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"]
  }},

  "facebook_reels": {{
    "caption": "Reels caption. Under 90 chars. Punchy. Creates FOMO. Works without sound.",
    "hashtags": ["#reel1","#reel2","#reel3","#reel4","#reel5"],
    "audio_suggestion": "Trending audio style that fits this content — e.g. 'dramatic news stinger' or 'lo-fi ambient'"
  }},

  "tiktok": {{
    "caption": "TikTok caption. Under 150 chars including hashtags. Hooks in first 5 words. Casual, native TikTok voice. Include 1 direct question.",
    "hashtags": ["#fyp","#tag2","#tag3","#tag4","#tag5","#tag6","#tag7"],
    "hook_text_overlay": "The text overlay for the first 3 seconds of the clip — 6 words max, creates immediate curiosity",
    "sound_suggestion": "Type of trending sound that fits — e.g. 'dramatic reveal sound', 'news ticker', 'suspense build'"
  }},

  "twitter": {{
    "tweet_1": "First tweet — the hook. Under 240 chars. Bold claim or question. Ends with 🧵 to signal thread.",
    "tweet_2": "Second tweet — the tension builder. Under 240 chars. Reveals the core insight without giving everything away.",
    "tweet_3": "Third tweet — the payoff + CTA. Under 240 chars. Ends with video link placeholder [LINK] and one question for replies.",
    "hashtags": ["#tag1","#tag2"]
  }},

  "telegram": {{
    "channel_post": "Telegram channel post. 60-90 words. Direct, no fluff. Telegram audiences hate marketing speak. Tell them exactly what the video is and why it matters right now. Include the YouTube link placeholder [YT_LINK].",
    "community_prompt": "If posting in a community group — a genuine discussion question that makes members want to reply. 1-2 sentences."
  }}
}}"""

    try:
        r = requests.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key":         anthropic_key,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json={
                "model":      CLAUDE_MODEL,
                "max_tokens": 2000,
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=45,
        )
        r.raise_for_status()
        raw = r.json()["content"][0]["text"].strip()
        raw = raw.lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(raw)

    except json.JSONDecodeError as e:
        return _fallback_captions(video_title)
    except Exception as e:
        return _fallback_captions(video_title)


def _fallback_captions(title):
    """Basic captions when Claude is unavailable."""
    return {
        "youtube":        {"title": title, "description": title, "tags": [], "end_screen_suggestion": ""},
        "facebook_feed":  {"caption": title, "hashtags": []},
        "facebook_reels": {"caption": title, "hashtags": [], "audio_suggestion": ""},
        "tiktok":         {"caption": title, "hashtags": ["#fyp"], "hook_text_overlay": "", "sound_suggestion": ""},
        "twitter":        {"tweet_1": title, "tweet_2": "", "tweet_3": "[LINK]", "hashtags": []},
        "telegram":       {"channel_post": f"{title} [YT_LINK]", "community_prompt": "What do you think?"},
    }
