"""
VIDEO SORCERER — AI Director
==============================
Martin Scorsese meets NotebookLM meets MrBeast.

The AI Director reads the full script and makes every
creative decision a human director would make —
but in seconds, with perfect consistency, and with
deep knowledge of what makes content go viral.

15 Intelligence Features:
  1.  Audience Emotion Tracker
  2.  Cultural Context Engine
  3.  Viral Moment Predictor
  4.  Comment Anticipator
  5.  Dynamic Colour Narrative
  6.  Typography Personality
  7.  Invisible Editing
  8.  Sound Architecture
  9.  B-Roll Meaning Engine
  10. Continuity Director
  11. Silence Composer
  12. Replayability Score
  13. Revenue Optimiser
  14. Monetisation Mode
  15. Cinematic Depth (3D) — NEW: Designs z-axis depth and 3D rotations.

One Claude Opus call. Complete visual direction document.
Cost: ~$0.15 per video directed.
"""

import json
import requests

CLAUDE_MODEL  = "claude-opus-4-5"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

# ── Style DNA definitions ──────────────────────────────────────────────────────
STYLE_DNA = {
    "scorsese": {
        "cuts_per_minute":   8,
        "colour_approach":   "Rich, saturated, deliberate. Colour tells the story.",
        "typography":        "Heavy serif for gravity. Clean sans for disruption.",
        "silence_frequency": "High — silence is used as a weapon",
        "energy_curve":      "Slow burn that explodes",
        "pacing_philosophy": "Every frame must earn its place",
    },
    "mrbeast": {
        "cuts_per_minute":   24,
        "colour_approach":   "Oversaturated, high contrast, pure energy",
        "typography":        "Bold, chunky, animated, always on screen",
        "silence_frequency": "Almost never — constant stimulation",
        "energy_curve":      "100% from second one, never drops",
        "pacing_philosophy": "If it can be cut, cut it",
    },
    "capcut": {
        "cuts_per_minute":   40,
        "colour_approach":   "Trending palettes, colour pop, viral aesthetics",
        "typography":        "Flying text, emoji integration, reaction fonts",
        "silence_frequency": "Never — trending audio always present",
        "energy_curve":      "Addictive loop — designed to replay",
        "pacing_philosophy": "Optimised for 9-second attention span",
    },
    "hybrid": {
        "cuts_per_minute":   16,
        "colour_approach":   "Documentary depth with viral energy pops",
        "typography":        "Authority serif for facts, impact for reveals",
        "silence_frequency": "Strategic — used for maximum contrast",
        "energy_curve":      "Scorsese foundation with MrBeast moments",
        "pacing_philosophy": "Replayable depth with instant accessibility",
    },
}

# ── Character archetypes ───────────────────────────────────────────────────────
CHARACTER_ARCHETYPES = {
    "victim":   "Someone losing something. Fear trigger. Tight frames, cold tones.",
    "hero":     "Someone beating the odds. Hope trigger. Wide frames, warm tones.",
    "villain":  "The system or force causing harm. Anger trigger. Cold blue, sharp cuts.",
    "oracle":   "The expert who sees what others don't. Authority trigger. Clean frames, measured pace.",
    "everyman": "This could be you. Personal trigger. Mid shots, relatable visuals.",
    "trickster":"The unexpected truth-teller. Surprise trigger. Whip pans, colour pops.",
}

# ── Cultural colour meanings ───────────────────────────────────────────────────
CULTURAL_COLOUR_MAP = {
    "global": {
        "red":    "danger, urgency, passion",
        "blue":   "trust, technology, calm",
        "green":  "money, growth, health",
        "gold":   "wealth, achievement, premium",
        "black":  "power, sophistication, death",
        "white":  "clarity, hope, new beginning",
    },
    "africa": {
        "red":    "sacrifice, strength",
        "green":  "land, fertility, prosperity",
        "gold":   "royalty, wealth, sun",
        "black":  "maturity, spiritual energy",
    },
    "asia": {
        "red":    "luck, celebration, prosperity",
        "white":  "mourning, death — use carefully",
        "gold":   "imperial, divine, wealth",
        "green":  "new life, youth",
    },
}


# ── Main director function ─────────────────────────────────────────────────────
def direct(script, style="hybrid", target_culture="global",
           aspect_ratio="16:9", channel_history=None, 
           anthropic_key=None, log_fn=print):
    """
    The AI Director reads the full script and produces a complete
    visual direction document.

    Args:
        script          : full script dict from scriptwriter
        style           : "scorsese", "mrbeast", "capcut", "hybrid"
        target_culture  : "global", "africa", "asia" — affects colour choices
        channel_history : list of past direction docs (for style memory)
        anthropic_key   : Anthropic API key

    Returns:
        Complete direction document dict
    """
    if not anthropic_key:
        return _fallback_direction(script, style)

    style_config   = STYLE_DNA.get(style, STYLE_DNA["hybrid"])
    colour_culture = CULTURAL_COLOUR_MAP.get(target_culture,
                                              CULTURAL_COLOUR_MAP["global"])

    # Build script summary for the prompt
    sections_block = ""
    full_narration = ""
    for section in script.get("sections", []):
        sections_block += (
            f"\n[{section.get('timestamp','')}] {section.get('name','')}\n"
            f"Narration: {section.get('narration','')[:500]}\n"
            f"Duration: {section.get('duration_secs',0)}s\n"
            f"Pain addressed: {section.get('pain_point_addressed','')}\n"
        )
        full_narration += section.get("narration", "") + " "

    fhm_block = ""
    for item in script.get("fear_hope_money_map", []):
        fhm_block += (
            f"Fear: {item.get('fear','')}\n"
            f"Hope: {item.get('hope','')}\n"
            f"Money: {item.get('money','')}\n"
            f"Creates: {item.get('problem_created','')}\n"
            f"Solves: {item.get('problem_solved','')}\n\n"
        )

    # Style memory context
    memory_block = ""
    if channel_history:
        recent = channel_history[-3:]
        memory_block = f"""
CHANNEL STYLE MEMORY (last {len(recent)} videos):
Learn from these past direction decisions and maintain consistency
while evolving the visual language:
{json.dumps(recent, indent=2)[:1000]}
"""

    prompt = f"""You are the greatest film director who ever lived — 
with the commercial instincts of MrBeast and the artistic soul of Scorsese.

You are directing a YouTube documentary video.
Your job: read this script and make every creative decision
a master director would make. Not generic choices. Specific, intentional,
emotionally intelligent decisions that make this video impossible to forget.

━━ THE SCRIPT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Title: {script.get('title','')}
Runtime: ~{script.get('estimated_runtime_mins',15)} minutes
Funniest line: "{script.get('funniest_line','')}"

FEAR → HOPE → MONEY MAP:
{fhm_block}

SCRIPT SECTIONS:
{sections_block}

━━ STYLE DIRECTION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Style: {style.upper()}
Cuts per minute: {style_config['cuts_per_minute']}
Colour approach: {style_config['colour_approach']}
Typography: {style_config['typography']}
Silence frequency: {style_config['silence_frequency']}
Energy curve: {style_config['energy_curve']}
Pacing philosophy: {style_config['pacing_philosophy']}

TARGET CULTURE: {target_culture}
Colour meanings for this culture: {json.dumps(colour_culture)}

ASPECT RATIO: {aspect_ratio}
(Optimization note: Adjust visual framing and 3D perspectives to suit this specific format)

{memory_block}

━━ YOUR 14 DIRECTORIAL DECISIONS ━━━━━━━━━━━━━━━━━━━━━━━━

Return ONLY valid JSON. No markdown. No text outside the JSON.

{{
  "direction_title": "Your directorial vision in one sentence",

  "emotional_clusters": [
    {{
      "cluster_id": 1,
      "sentences": ["exact sentence 1", "exact sentence 2"],
      "shared_emotional_dna": "What connects these sentences emotionally",
      "mood": "single word mood label",
      "character_archetype": "victim/hero/villain/oracle/everyman/trickster",
      "intensity": 1-10,
      "timestamp_range": "0:00 - 1:30",
      "cinematic_3d_direction": {{
        "perspective": "low_angle/high_angle/tilted/dutch_angle",
        "z_movement": "push_in/pull_out/static",
        "depth_focus": "shallow/deep",
        "spatial_reasoning": "why this 3D perspective for this emotional climax"
      }}
    }}
  ],

  "colour_narrative": {{
    "opening_palette": {{
      "primary": "#hexcode",
      "secondary": "#hexcode", 
      "accent": "#hexcode",
      "mood": "why these colours for the opening"
    }},
    "journey": [
      {{
        "timestamp": "0:00",
        "palette": {{"primary": "#hex", "secondary": "#hex", "accent": "#hex"}},
        "transition_type": "gradual/sudden/flash",
        "emotional_reason": "why the colour shifts here"
      }}
    ],
    "climax_palette": {{
      "primary": "#hexcode",
      "secondary": "#hexcode",
      "accent": "#hexcode",
      "mood": "the most powerful visual moment"
    }},
    "colour_callbacks": [
      "A colour introduced in the fear section reappears at the consequence — creating subconscious continuity"
    ]
  }},

  "typography_plan": {{
    "primary_font": "Font name and why",
    "secondary_font": "Font name and why",
    "stat_font": "Font for numbers and data",
    "impact_font": "Font for shocking reveals",
    "channel_signature": "The typography choice that will become this channel's identity",
    "per_cluster_typography": [
      {{
        "cluster_id": 1,
        "font": "font choice",
        "size": "large/medium/small",
        "animation": "slam/fade/typewrite/float/none/3d_spin/3d_flip",
        "colour": "#hexcode",
        "z_depth": "-500 to 500",
        "rotation_y": "-45 to 45",
        "reasoning": "why this for this emotional moment"
      }}
    ]
  }},

  "silence_map": [
    {{
      "timestamp": "exact timestamp",
      "duration_secs": 2,
      "type": "complete/near/music_only",
      "purpose": "what this silence accomplishes emotionally",
      "what_precedes": "the line or moment before the silence",
      "what_follows": "what breaks the silence and why"
    }}
  ],

  "sound_architecture": {{
    "overall_soundscape": "The audio world of this video described as if explaining to a composer",
    "music_journey": [
      {{
        "timestamp": "0:00",
        "instruction": "Specific music direction — mood, tempo, instrumentation",
        "volume": "db level relative to narration",
        "transition": "how it changes from previous"
      }}
    ],
    "sfx_moments": [
      {{
        "timestamp": "exact timestamp",
        "sound": "specific sound effect description",
        "emotional_purpose": "why this sound at this moment",
        "search_keyword": "what to search for in Freesound"
      }}
    ],
    "audio_callbacks": [
      "A sound motif introduced early that returns transformed at the climax"
    ]
  }},

  "viral_moment": {{
    "timestamp": "exact timestamp",
    "narration_line": "The exact line that will be clipped millions of times",
    "why_viral": "The specific psychological mechanism",
    "enhancement_instructions": "How to make this moment even more powerful visually and aurally",
    "predicted_platform": "TikTok/Reels/Shorts/Twitter",
    "clip_start_secs": 0,
    "clip_end_secs": 30
  }},

  "comment_predictions": [
    {{
      "predicted_comment": "Exact type of comment people will write",
      "timestamp_trigger": "Which moment triggers this",
      "volume": "hundreds/thousands/tens of thousands",
      "edit_enhancement": "How to make this moment trigger even more comments"
    }}
  ],

  "invisible_editing_rules": [
    {{
      "timestamp": "timestamp",
      "rule": "The specific editing decision",
      "reason": "Why breaking or following convention here serves the story",
      "audience_feeling": "What the audience feels without knowing why"
    }}
  ],

  "continuity_elements": [
    {{
      "element": "visual/colour/sound/text",
      "introduced_at": "timestamp",
      "returns_at": "timestamp",
      "transformation": "How it has changed — and what that change means",
      "audience_effect": "The subconscious connection this creates"
    }}
  ],

  "replayability_score": {{
    "score": 8,
    "hidden_layers": [
      "Detail that rewards second viewing"
    ],
    "improvements": [
      "Specific addition that would increase the score"
    ],
    "most_replayable_moment": "The single moment most likely to make someone restart the video"
  }},

  "revenue_optimisation": {{
    "ad_placements": [
      {{
        "timestamp": "exact timestamp",
        "type": "pre-roll/mid-roll/post-roll",
        "reason": "Why placing an ad here maximises both revenue and retention",
        "retention_risk": "low/medium/high",
        "estimated_cpm_boost": "percentage improvement over random placement"
      }}
    ],
    "highest_value_section": "The section with the most advertiser-friendly content",
    "estimated_rpm": "Realistic RPM for this niche and audience"
  }},

  "monetisation_safety": {{
    "overall_rating": "green/yellow/red",
    "flagged_moments": [
      {{
        "timestamp": "timestamp",
        "issue": "what could trigger demonetisation",
        "fix": "exact replacement"
      }}
    ],
    "safe_to_publish": true,
    "confidence": 95
  }},

  "broll_meaning_assignments": [
    {{
      "cluster_id": 1,
      "emotional_requirement": "What the footage must make the audience feel",
      "literal_keywords": ["keyword1", "keyword2"],
      "emotional_keywords": ["the feeling not the thing"],
      "avoid": ["footage that would undercut the emotion"],
      "hero_shot_description": "If a Kling AI shot is warranted, describe it in detail"
    }}
  ],

  "directors_commentary": {{
    "overall_vision": "Your complete artistic statement for this video",
    "most_important_decision": "The single most important directorial choice and why",
    "biggest_risk": "What could go wrong and why you made the choice anyway",
    "what_makes_this_replayable": "The deep reason audiences will watch this twice",
    "scorsese_lesson": "The filmmaking principle this video teaches the creator",
    "mrbeast_lesson": "The virality principle embedded in this edit",
    "capcut_lesson": "The social media instinct used in this video"
  }},

  "audience_emotion_timeline": [
    {{
      "timestamp": "0:00",
      "emotion": "primary emotion audience feels",
      "intensity": 1-10,
      "attention_risk": "low/medium/high — risk of losing viewer here",
      "intervention": "what the edit does to maintain attention"
    }}
  ],

  "cultural_adaptations": [
    {{
      "element": "colour/symbol/reference",
      "global_meaning": "what it means worldwide",
      "cultural_meaning": "what it means for target culture",
      "adaptation": "how the edit accounts for this"
    }}
  ]
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
                "max_tokens": 12000,
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=120,
        )
        r.raise_for_status()
        raw = r.json()["content"][0]["text"].strip()
        raw = raw.lstrip("```json").lstrip("```").rstrip("```").strip()
        direction = json.loads(raw)
        direction["style"]           = style
        direction["target_culture"]  = target_culture
        direction["style_config"]    = style_config
        return direction

    except json.JSONDecodeError as e:
        return {"_error": f"JSON parse failed: {e}", "_raw": raw[:500]}
    except Exception as e:
        return {"_error": str(e)}


def vet_direction(script, direction, anthropic_key, log_fn=print):
    """
    Acts as a 'Cynical Executive Producer' to find flaws in the direction doc.
    """
    if not anthropic_key or not direction or direction.get("_error"):
        return None

    log_fn("  🧐 Vetting production plan (Executive Producer loop)...")

    prompt = f"""You are a Cynical Executive Producer with 40 years of experience in high-end documentary filmmaking and viral YouTube production.
You have been handed a Visual Direction document for a project. Your job is to find the weak points, the logical gaps, and the "hallucinations" before we spend any money on production.

━━ THE SCRIPT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{json.dumps(script, indent=2)[:5000]}

━━ THE PROPOSED DIRECTION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{json.dumps(direction, indent=2)[:8000]}

━━ YOUR QUALITY CHECKLIST ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Hallucinations: Does it suggest SFX or visuals that don't match the script?
2. Colour Narrative: Does the journey actually make sense for the emotion, or is it just random?
3. Viral Moment: Is the selected line actually a hook, or just filler?
4. Technical Pacing: Are timestamps consistent? Are SFX properly spaced?
5. Character Archetypes: Do they match the narration's tone?

Return a JSON report with your critiques.

Return ONLY valid JSON:
{{
  "overall_quality": 1-10,
  "lethal_flaws": ["critical issues that will ruin the video"],
  "minor_annoyances": ["small polish points"],
  "suggested_fixes": [
    {{
      "field": "section name or path to the value in the direction JSON",
      "issue": "what is wrong",
      "fix": "exact replacement value or instruction"
    }}
  ]
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
                "max_tokens": 4000,
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        r.raise_for_status()
        raw = r.json()["content"][0]["text"].strip()
        raw = raw.lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(raw)
    except Exception as e:
        log_fn(f"  ⚠ Vetting failed: {e}")
        return None


def apply_fixes(direction, vetting_report, anthropic_key, log_fn=print):
    """
    Applies the EP's suggested fixes to the direction document.
    """
    if not vetting_report or not vetting_report.get("suggested_fixes"):
        return direction

    log_fn(f"  🛠 Applying {len(vetting_report['suggested_fixes'])} corrections from the EP...")

    prompt = f"""You are a Lead Editor. You have an original Direction document and an Executive Producer's Vetting Report.
Your job is to produce the FINAL, perfect version of the Direction document by applying the EP's fixes.

━━ ORIGINAL DIRECTION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{json.dumps(direction, indent=2)[:8000]}

━━ VETTING REPORT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{json.dumps(vetting_report, indent=2)}

Return ONLY the complete, final JSON direction document. No text outside JSON. No explanation."""

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
                "max_tokens": 12000,
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=90,
        )
        r.raise_for_status()
        raw = r.json()["content"][0]["text"].strip()
        raw = raw.lstrip("```json").lstrip("```").rstrip("```").strip()
        final_dir = json.loads(raw)
        final_dir["vetted"] = True
        return final_dir
    except Exception as e:
        log_fn(f"  ⚠ Fix application failed: {e}")
        return direction


# ── Fallback when no API key ───────────────────────────────────────────────────
def _fallback_direction(script, style):
    """Basic direction when Claude is not available."""
    config = STYLE_DNA.get(style, STYLE_DNA["hybrid"])
    sections = script.get("sections", [])

    clusters = []
    for i, section in enumerate(sections):
        clusters.append({
            "cluster_id":         i + 1,
            "sentences":          [section.get("narration", "")[:100]],
            "shared_emotional_dna": section.get("pain_point_addressed", ""),
            "mood":               "neutral",
            "character_archetype": "everyman",
            "intensity":          5,
            "timestamp_range":    section.get("timestamp", "0:00"),
        })

    return {
        "direction_title": f"Standard {style} direction",
        "style":           style,
        "style_config":    config,
        "emotional_clusters": clusters,
        "colour_narrative": {
            "opening_palette": {"primary": "#000000", "secondary": "#ffffff", "accent": "#ff3355"},
            "journey": [],
            "climax_palette": {"primary": "#ff3355", "secondary": "#000000", "accent": "#ffffff"},
        },
        "replayability_score": {"score": 6, "hidden_layers": [], "improvements": []},
        "monetisation_safety": {"overall_rating": "green", "safe_to_publish": True},
        "directors_commentary": {
            "overall_vision": "Standard documentary assembly",
            "scorsese_lesson": "Let the story breathe",
            "mrbeast_lesson":  "Never drop the energy",
            "capcut_lesson":   "Make every second count",
        },
        "_fallback": True,
    }


# ── Format direction for Telegram ─────────────────────────────────────────────
def format_direction_telegram(direction):
    """Send the director's vision to Telegram."""
    if not direction or direction.get("_error"):
        return None

    comm  = direction.get("directors_commentary", {})
    viral = direction.get("viral_moment", {})
    rep   = direction.get("replayability_score", {})
    safe  = direction.get("monetisation_safety", {})
    rev   = direction.get("revenue_optimisation", {})

    safety_emoji = {"green": "✅", "yellow": "⚠️", "red": "🚨"}.get(
        safe.get("overall_rating", "green"), "✅"
    )

    msg = (
        f"🎬 <b>AI DIRECTOR'S VISION</b>\n"
        f"─────────────────────────\n\n"
        f"<b>{direction.get('direction_title','')}</b>\n\n"

        f"🎭 <b>Director's Statement</b>\n"
        f"{comm.get('overall_vision','')}\n\n"

        f"🔴 <b>Viral Moment</b>\n"
        f"Timestamp: {viral.get('timestamp','')}\n"
        f"<i>\"{viral.get('narration_line','')}\"</i>\n"
        f"Platform: {viral.get('predicted_platform','')}\n"
        f"Why: {viral.get('why_viral','')}\n\n"

        f"🔁 <b>Replayability: {rep.get('score','?')}/10</b>\n"
        f"{rep.get('most_replayable_moment','')}\n\n"

        f"💰 <b>Revenue</b>\n"
        f"Est. RPM: {rev.get('estimated_rpm','')}\n\n"

        f"{safety_emoji} <b>Monetisation: {safe.get('overall_rating','').upper()}</b>\n"
        f"Safe to publish: {'Yes' if safe.get('safe_to_publish') else 'No'} "
        f"({safe.get('confidence',0)}% confidence)\n\n"

        f"🎓 <b>Lessons from the Director</b>\n"
        f"Scorsese: {comm.get('scorsese_lesson','')}\n"
        f"MrBeast: {comm.get('mrbeast_lesson','')}\n"
        f"CapCut: {comm.get('capcut_lesson','')}"
    )

    return msg


# ── Format full direction for terminal ────────────────────────────────────────
def format_direction_terminal(direction):
    """Full direction document for terminal/log output."""
    if not direction or direction.get("_error"):
        return f"  ⚠ Direction error: {direction.get('_error','unknown')}"

    W    = 65
    comm = direction.get("directors_commentary", {})
    viral = direction.get("viral_moment", {})
    rep  = direction.get("replayability_score", {})
    safe = direction.get("monetisation_safety", {})

    lines = [
        "",
        "═" * W,
        f"  🎬  AI DIRECTOR — {direction.get('style','').upper()} STYLE",
        "═" * W,
        f"  Vision: {direction.get('direction_title','')}",
        "",
        "─" * W,
        "  🎭  EMOTIONAL CLUSTERS",
    ]

    for cluster in direction.get("emotional_clusters", [])[:5]:
        lines += [
            f"  [{cluster.get('timestamp_range','')}] "
            f"{cluster.get('mood','').upper()} — "
            f"{cluster.get('character_archetype','').upper()} — "
            f"Intensity {cluster.get('intensity',0)}/10",
            f"  DNA: {cluster.get('shared_emotional_dna','')}",
            "",
        ]

    lines += [
        "─" * W,
        "  🔴  VIRAL MOMENT",
        f"  Timestamp : {viral.get('timestamp','')}",
        f"  Platform  : {viral.get('predicted_platform','')}",
        f"  Line      : \"{viral.get('narration_line','')}\"",
        f"  Why       : {viral.get('why_viral','')}",
        "",
        "─" * W,
        f"  🔁  REPLAYABILITY: {rep.get('score','?')}/10",
    ]

    for layer in rep.get("hidden_layers", [])[:3]:
        lines.append(f"  › {layer}")

    lines += [
        "",
        "─" * W,
        f"  ✅  MONETISATION: {safe.get('overall_rating','').upper()}",
        f"  Safe to publish: {'Yes' if safe.get('safe_to_publish') else 'No'}",
        "",
        "─" * W,
        "  🎓  DIRECTOR'S COMMENTARY",
        f"  {comm.get('overall_vision','')}",
        "",
        f"  Scorsese lesson : {comm.get('scorsese_lesson','')}",
        f"  MrBeast lesson  : {comm.get('mrbeast_lesson','')}",
        f"  CapCut lesson   : {comm.get('capcut_lesson','')}",
        "",
        "═" * W,
        "",
    ]

    return "\n".join(lines)
