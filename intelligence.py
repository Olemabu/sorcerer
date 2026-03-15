"""
SORCERER — Intelligence Layer
Fires ONLY after a signal is confirmed by the engine.
One Claude API call per alert. Costs ~$0.01.

Returns:
  - What the comment section is feeling
  - Why it's really spiking
  - The exact video angle you should make
  - Recommended length + reasoning
  - Whether to push ads + audience + timing
"""

import json
import requests


CLAUDE_MODEL = "claude-sonnet-4-6"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


def analyse(video, signal, baseline, comments, anthropic_key):
    """
    Send spike data + top comments to Claude.
    Returns a structured dict or None if key missing / parse fails.
    """
    if not anthropic_key:
        return None

    comment_block = "\n".join(
        f'- [{c["likes"]} likes] {c["text"]}'
        for c in comments
    ) if comments else "Comments not available for this video."

    competitor_len  = video.get("duration_mins", "?")
    channel_avg_len = baseline.get("median_duration", "?")

    prompt = f"""You are a sharp YouTube content strategist working for a creator.
A competitor video just spiked hard. Your job: tell the creator exactly what to do next.
Be specific. Be direct. No fluff.

━━ SPIKING VIDEO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Title         : {video['title']}
Channel       : {video['channel_title']}
Age           : {video['age_hours']} hours old
Views         : {video['views']:,}
Views/hr now  : {video['views_per_hour']:,.0f}
Channel avg   : {baseline['median_vph']:,.0f} views/hr
Spike         : {signal['multiplier']}× above their own baseline
Video length  : {competitor_len} min
Their avg len : {channel_avg_len} min
Likes         : {video['likes']:,}
Comments      : {video['comment_count']:,}
Signal window : {signal['window']}

━━ TOP COMMENTS (most liked first) ━━━━━━━━━━━
{comment_block}

━━ YOUR TASK ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Return ONLY valid JSON. No markdown. No explanation outside the JSON object.

{{
  "comment_pulse": "2-3 sentences. What emotion is driving engagement? What debate or question keeps repeating? What are people actually saying in the top comments?",

  "why_spiking": "1-2 sentences. The REAL reason this blew up. Go beyond the topic — what timing, emotion, or algorithm factor is fueling it?",

  "my_video_angle": "A killer title/angle the creator should make. Specific. Punchy. Better than the competitor's. Not a generic summary.",

  "hook_idea": "The first 20 seconds. What should the creator say or show to immediately grab attention and make people stay?",

  "recommended_length_mins": <integer — the optimal length in minutes>,

  "length_reasoning": "One sentence. Why this length beats the competitor.",

  "content_structure": [
    "Step 1 — what to cover and why",
    "Step 2 — what to cover and why",
    "Step 3 — what to cover and why",
    "Step 4 — what to cover and why"
  ],

  "worth_pushing_ads": <true or false>,

  "ad_reasoning": "One sentence. Why push or why not.",

  "target_audience": ["segment 1", "segment 2", "segment 3"],

  "ad_timing": "Exact timing recommendation, e.g. '6 hours after upload once organic velocity confirms'",

  "estimated_budget": "Suggested daily ad spend range, e.g. '$30–60/day for 3 days'",

  "urgency_note": "One sentence. How much time does the creator realistically have before this window closes?"
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
                "max_tokens": 1200,
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=45,
        )
        r.raise_for_status()
        raw = r.json()["content"][0]["text"].strip()
        raw = raw.lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(raw)

    except json.JSONDecodeError as e:
        return {"_error": f"JSON parse failed: {e}", "_raw": raw[:300]}
    except Exception as e:
        return {"_error": str(e)}
