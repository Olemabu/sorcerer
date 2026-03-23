"""
SORCERER — Concept Lab
========================
Proactive viral idea generator.
Instead of waiting for something to go viral, this module CREATES the idea.

Fully AI-driven — Claude invents wildly creative video series concepts
from scratch, scores them, and generates full series bibles with pilot scripts
that plug directly into the existing production pipeline.

Usage:
  /concept              — Generate 5 wild series ideas (scored)
  /concept tech         — Steer ideas toward a niche
  /concept pick 1       — Generate full series bible for concept #1
  /conceive             — Generate + produce a pilot episode in one shot
"""

import os
from api_utils import claude_request

# ── Model ──────────────────────────────────────────────────────────────────────
_MODEL_MAP = {
    "opus":   "claude-opus-4-5-20250514",
    "sonnet": "claude-sonnet-4-6",
}
_model_choice = os.getenv("CONCEPT_MODEL", "sonnet").lower().strip()
CONCEPT_MODEL = _MODEL_MAP.get(_model_choice, _MODEL_MAP["sonnet"])

# Use Opus for the full series bible (needs more creative depth)
BIBLE_MODEL = _MODEL_MAP.get(
    os.getenv("BIBLE_MODEL", "opus").lower().strip(),
    _MODEL_MAP["opus"],
)


# ── Concept Generation ─────────────────────────────────────────────────────────
def generate_concepts(anthropic_key, niche_hint=None, n=5, log_fn=print):
    """
    Ask Claude to invent N wildly creative, intriguing video series concepts.
    Returns a list of concept dicts sorted by virality score, or {"_error": "..."}.
    """
    if not anthropic_key:
        return {"_error": "No ANTHROPIC_API_KEY — concept generation requires Claude."}

    niche_line = ""
    if niche_hint:
        niche_line = (
            f"\nNICHE DIRECTION: The user wants ideas in or around the '{niche_hint}' space. "
            f"But don't be boring about it — twist it. Make it weird. Combine it with something "
            f"unexpected. The best viral concepts come from smashing two unrelated worlds together."
        )

    prompt = f"""You are the world's most creative viral content strategist. You have studied every 
weird YouTube Shorts channel that blew up from nothing — the channels with bizarre characters, 
surreal art styles, and concepts so strange that people can't stop watching.

Think about the channels that came out of nowhere:
- A clay-animated medieval peasant reacting to modern technology
- A creepy AI narrator ranking "cursed" foods in a liminal space aesthetic
- Historical figures debating modern problems in oil painting style
- A grandma character rating gen-z slang with chaotic energy
- Surreal "what if" scenarios animated in unsettling paper cutout style

Your job: invent {n} COMPLETELY ORIGINAL video series concepts that are so intriguing, 
so weird, so visually unique that they would stop someone mid-scroll.
{niche_line}

CRITICAL RULES:
1. Each concept MUST have a distinctive, memorable ART STYLE that has never been done before.
   Think: claymation meets brutalist architecture, retro VHS medical tapes, 
   Soviet propaganda poster animation, Victorian etching style with neon accents,
   corrupted digital art, Renaissance painting but everything is slightly wrong,
   paper-craft stop-motion, chalk on asphalt timelapse, woodblock print animation...
   THE ART STYLE IS WHAT MAKES PEOPLE STOP SCROLLING.

2. Each concept must be a SERIES — a repeatable format with infinite episode potential.
   If you can't immediately think of 20 episodes, the format isn't strong enough.

3. The concept must work as YouTube Shorts (60s) OR long-form (10-20 min). Versatile.

4. Suggest a channel name for each — something memorable, brandable, weird.

5. Think about what makes people SHARE. Concepts that make someone say 
   "you HAVE to see this channel" to a friend.

Return ONLY valid JSON. No markdown. No text outside the JSON.

{{
  "concepts": [
    {{
      "rank": 1,
      "title": "The concept name / series title",
      "pitch": "One electrifying sentence that sells the whole idea",
      "channel_name": "Suggested channel name",
      "art_style": "Detailed description of the unique visual style — be extremely specific about medium, texture, color palette, mood, influences. This should sound like nothing that exists on YouTube right now.",
      "format": "How each episode works — the repeatable structure",
      "tone": "The emotional register — deadpan? chaotic? unsettling? wholesome-but-wrong?",
      "example_episodes": [
        "Episode 1 title / idea",
        "Episode 2 title / idea",
        "Episode 3 title / idea",
        "Episode 4 title / idea",
        "Episode 5 title / idea"
      ],
      "why_viral": "Specific psychological reason this would spread — what human instinct does it exploit?",
      "target_audience": "Who watches this and why they can't stop",
      "virality_score": 8,
      "virality_reasoning": "Honest assessment of why this score"
    }}
  ]
}}

Sort by virality_score descending. The #1 concept should be the one you'd bet your career on."""

    log_fn("  🧪 Concept Lab: generating ideas...")
    result = claude_request(
        model=CONCEPT_MODEL,
        prompt=prompt,
        api_key=anthropic_key,
        max_tokens=6000,
        timeout=60,
        retries=2,
        backoff=5.0,
        log_fn=log_fn,
    )

    if result.get("_error"):
        return result

    concepts = result.get("concepts", [])
    if not concepts:
        return {"_error": "Claude returned no concepts", "_raw": str(result)[:500]}

    # Sort by virality score descending
    concepts.sort(key=lambda c: c.get("virality_score", 0), reverse=True)
    log_fn(f"  ✓ Generated {len(concepts)} concepts (top: {concepts[0].get('title', '?')})")
    return concepts


# ── Series Bible ───────────────────────────────────────────────────────────────
def generate_series_bible(concept, anthropic_key, log_fn=print):
    """
    Take a chosen concept and generate a full series bible with pilot script.
    The pilot script uses the same JSON format as scriptwriter.py so it plugs
    directly into narrator.py → compositor.py → full video.
    """
    if not anthropic_key:
        return {"_error": "No ANTHROPIC_API_KEY"}

    prompt = f"""You are a showrunner creating a complete series bible and pilot episode script 
for a new viral video channel.

THE CONCEPT:
Title: {concept.get('title', '')}
Pitch: {concept.get('pitch', '')}
Channel name: {concept.get('channel_name', '')}
Art style: {concept.get('art_style', '')}
Format: {concept.get('format', '')}
Tone: {concept.get('tone', '')}
Target audience: {concept.get('target_audience', '')}

Your job: create a COMPLETE series bible AND a full pilot episode script.

The pilot script must be a COMPLETE word-for-word narration — every single word the 
narrator will say. Not an outline. Not bullet points. THE ACTUAL WORDS.
A human must be able to press record and read it with ZERO preparation.

If a section is 60 seconds, that's ~150 words of narration.
COUNT YOUR WORDS. Every section needs full spoken narration.

CRITICAL: The art style described above must be woven into every visual direction.
Every [VISUAL CUE] must reference the specific art style, medium, and aesthetic.

Return ONLY valid JSON:

{{
  "series_bible": {{
    "channel_names": ["Option 1", "Option 2", "Option 3"],
    "tagline": "The channel's one-line identity",
    "format_description": "Exactly how each episode works — the repeatable formula in detail",
    "art_style_guide": {{
      "medium": "Primary visual medium (e.g. claymation, chalk art, digital collage)",
      "color_palette": "Specific colors — hex codes or vivid descriptions",
      "texture": "What the visuals feel like — gritty? smooth? corrupted? handmade?",
      "mood": "The emotional atmosphere of the visuals",
      "influences": "What this looks like crossed with what",
      "thumbnail_style": "How thumbnails should look to stop the scroll"
    }},
    "target_audience": {{
      "primary": "Core viewer description",
      "age_range": "e.g. 16-35",
      "platforms": ["YouTube Shorts", "TikTok", "Instagram Reels"],
      "why_addictive": "Why they will binge this"
    }},
    "estimated_cpm": "$X-Y range",
    "episodes": [
      {{
        "number": 1,
        "title": "Episode title",
        "hook": "The opening line or moment",
        "premise": "What happens in this episode"
      }},
      {{
        "number": 2,
        "title": "Episode title", 
        "hook": "The opening line or moment",
        "premise": "What happens"
      }}
    ],
    "growth_strategy": "How this channel goes from 0 to 100K subscribers"
  }},

  "pilot_script": {{
    "title": "Pilot episode title — must create massive curiosity gap",
    "title_alternatives": ["Alt 1", "Alt 2", "Alt 3"],
    "thumbnail": {{
      "background": "Exact visual description",
      "main_image": "What to show",
      "text_overlay": "Max 4 words",
      "color_scheme": "Exact colors",
      "gemini_prompt": "A hyper-detailed prompt for Google Gemini to generate this thumbnail."
    }},
    "seo_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "description_hook": "First 2 lines of the video description",
    "estimated_runtime_mins": 3,
    "funniest_line": "The best line in the whole script",
    "hook_score": "1-10 rating with explanation",
    "sections": [
      {{
        "name": "HOOK",
        "timestamp": "0:00",
        "duration_secs": 30,
        "mrbeast_energy": "What keeps this from being skippable",
        "visual_treatment": "Describe the exact visual style for this section using the art style guide",
        "pain_addressed": "The curiosity or emotion activated here",
        "narration": "THE COMPLETE WORD-FOR-WORD NARRATION. Every sentence spoken out loud. Weave in [VISUAL CUE: specific description matching the art style]. Weave in [PAUSE] for dramatic silence. Weave in [MUSIC: instruction]. Must be 100-300 words of actual spoken script.",
        "funny_moment": "The funny line in this section, or null",
        "open_loop": "What tension forces them to keep watching",
        "broll_keywords": ["keyword1", "keyword2", "keyword3"],
        "conversion_note": "What drives watch time here"
      }}
    ],
    "cta_narration": "Full word-for-word CTA. 15-30 seconds. Gets subscribe + comment.",
    "viral_prediction": "Honest assessment — will this pilot work? Why?"
  }}
}}

Make the episodes list 10 entries long. Make the pilot script have 3-5 sections 
depending on the target runtime. The pilot should demonstrate the format perfectly —
if someone watches just this one episode they understand exactly what the channel is."""

    log_fn("  📖 Concept Lab: generating series bible + pilot script...")
    result = claude_request(
        model=BIBLE_MODEL,
        prompt=prompt,
        api_key=anthropic_key,
        max_tokens=16000,
        timeout=120,
        retries=2,
        backoff=5.0,
        log_fn=log_fn,
    )

    if result.get("_error"):
        return result

    log_fn(f"  ✓ Series bible complete — {len(result.get('series_bible', {}).get('episodes', []))} episodes planned")
    return result


# ── Telegram Formatting ────────────────────────────────────────────────────────
def format_concepts_telegram(concepts):
    """Format scored concepts for Telegram display."""
    if isinstance(concepts, dict) and concepts.get("_error"):
        return f"❌ {concepts['_error']}"

    msg = "🧪 <b>CONCEPT LAB — VIRAL IDEAS</b>\n"
    msg += "─────────────────────────\n\n"

    for i, c in enumerate(concepts, 1):
        stars = "⭐" * min(c.get("virality_score", 0), 10)
        msg += (
            f"<b>#{i} — {c.get('title', '?')}</b>\n"
            f"💡 {c.get('pitch', '')}\n"
            f"🎨 <i>{c.get('art_style', '')[:120]}...</i>\n"
            f"📺 Channel: <b>{c.get('channel_name', '?')}</b>\n"
            f"🎯 {c.get('target_audience', '')}\n"
            f"🔥 Virality: {stars} ({c.get('virality_score', '?')}/10)\n"
            f"<i>{c.get('virality_reasoning', '')}</i>\n\n"
            f"📋 Episodes:\n"
        )
        for ep in c.get("example_episodes", [])[:3]:
            msg += f"  • {ep}\n"
        msg += f"  <i>...and more</i>\n\n"
        msg += "─────────────────────────\n\n"

    msg += (
        "💬 <b>Pick one!</b>\n"
        "Send <code>/concept pick 1</code> to generate a full series bible + pilot script.\n"
        "Send <code>/conceive 1</code> to produce the pilot episode right now."
    )
    return msg


def format_bible_telegram(bible):
    """Format series bible for Telegram display."""
    if isinstance(bible, dict) and bible.get("_error"):
        return f"❌ {bible['_error']}"

    sb = bible.get("series_bible", {})
    ps = bible.get("pilot_script", {})
    art = sb.get("art_style_guide", {})
    audience = sb.get("target_audience", {})

    msg = "📖 <b>SERIES BIBLE</b>\n"
    msg += "═════════════════════════\n\n"

    # Channel names
    names = sb.get("channel_names", [])
    if names:
        msg += "<b>Channel Name Options:</b>\n"
        for n in names:
            msg += f"  • <b>{n}</b>\n"
        msg += "\n"

    msg += f"📌 {sb.get('tagline', '')}\n\n"

    # Art style
    msg += (
        f"🎨 <b>ART STYLE</b>\n"
        f"Medium: {art.get('medium', '?')}\n"
        f"Palette: {art.get('color_palette', '?')}\n"
        f"Texture: {art.get('texture', '?')}\n"
        f"Mood: {art.get('mood', '?')}\n"
        f"Influences: {art.get('influences', '?')}\n\n"
    )

    # Format
    msg += f"📐 <b>FORMAT</b>\n{sb.get('format_description', '?')}\n\n"

    # Audience
    msg += (
        f"👥 <b>AUDIENCE</b>\n"
        f"{audience.get('primary', '?')} ({audience.get('age_range', '?')})\n"
        f"💰 Est. CPM: {sb.get('estimated_cpm', '?')}\n"
        f"🔁 {audience.get('why_addictive', '')}\n\n"
    )

    # Episodes
    episodes = sb.get("episodes", [])
    if episodes:
        msg += f"📋 <b>EPISODE PLAN ({len(episodes)} episodes)</b>\n"
        for ep in episodes[:5]:
            msg += f"  {ep.get('number', '?')}. <b>{ep.get('title', '?')}</b>\n"
            msg += f"     <i>{ep.get('premise', '')[:80]}</i>\n"
        if len(episodes) > 5:
            msg += f"  <i>...and {len(episodes) - 5} more</i>\n"
        msg += "\n"

    # Growth strategy
    if sb.get("growth_strategy"):
        msg += f"📈 <b>GROWTH STRATEGY</b>\n{sb['growth_strategy']}\n\n"

    # Pilot script summary
    msg += "═════════════════════════\n"
    msg += f"🎬 <b>PILOT SCRIPT</b>\n"
    msg += f"Title: <b>{ps.get('title', '?')}</b>\n"
    msg += f"Runtime: ~{ps.get('estimated_runtime_mins', '?')} min\n"
    msg += f"Hook: {ps.get('hook_score', '?')}\n\n"

    # Pilot sections
    sections = ps.get("sections", [])
    if sections:
        for section in sections[:2]:
            narration = section.get("narration", "")[:400]
            msg += (
                f"🎤 <b>[{section.get('timestamp', '')}] {section.get('name', '').upper()}</b>\n"
                f"<i>{narration}...</i>\n\n"
            )
        if len(sections) > 2:
            msg += f"<i>...plus {len(sections) - 2} more sections</i>\n\n"

    msg += (
        f"🔮 {ps.get('viral_prediction', '')}\n\n"
        f"Send <code>/conceive</code> to produce this pilot episode now."
    )
    return msg


def extract_pilot_as_script(bible):
    """
    Extract the pilot_script from a series bible and return it in the
    same format that scriptwriter.py produces — so it can be fed directly
    into narrator.py → compositor.py → full video pipeline.
    """
    return bible.get("pilot_script", {})
