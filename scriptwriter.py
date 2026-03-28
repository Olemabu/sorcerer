"""
SORCERER — Script Writer (Full Production Edition)
====================================================
Writes complete production-ready packages:
  - MrBeast energy + documentary style
  - Banned words filter (YouTube safe, monetisation safe)
  - Conversion-optimised everything
  - Full content plan not just script suggestions

Claude Opus only. This is the product.
"""

import json
import re
import os
import requests
from datetime import datetime
from pathlib import Path

from api_utils import claude_request

# ── Model selection ────────────────────────────────────────────────────────
# Set SCRIPT_MODEL in Railway Variables to switch without redeploying:
#   "opus"   → best quality, ~$0.08/script  (default)
#   "sonnet" → good quality, ~$0.01/script  (use when credits are low)
_MODEL_MAP = {
    "opus":   "claude-opus-4-5-20250514",
    "sonnet": "claude-sonnet-4-6",
}
_model_choice = os.getenv("SCRIPT_MODEL", "opus").lower().strip()
CLAUDE_MODEL  = _MODEL_MAP.get(_model_choice, _MODEL_MAP["opus"])

# ── YouTube banned/demonetised words to avoid ─────────────────────────────────
BANNED_WORDS = [
    "kill", "killed", "killing", "murder", "suicide", "bomb", "terrorist",
    "shooting", "massacre", "genocide", "rape", "porn", "sex", "naked",
    "drug", "cocaine", "heroin", "meth", "overdose", "shoot up",
    "dead body", "corpse", "blood", "gore", "weapon", "gun", "rifle",
    "explosive", "detonate", "virus spread", "pandemic death",
    "crisis", "tragedy", "catastrophe", "disaster"
]

# Safe replacements
SAFE_REPLACEMENTS = {
    "kill":       "eliminate",
    "killed":     "replaced",
    "killing":    "disrupting",
    "dead":       "obsolete",
    "crisis":     "turning point",
    "tragedy":    "challenge",
    "disaster":   "disruption",
    "catastrophe": "transformation",
    "virus":      "technology",
    "bomb":       "breakthrough",
}


def sanitise_script(text):
    """Replace banned words with safe alternatives."""
    for word, replacement in SAFE_REPLACEMENTS.items():
        text = re.sub(rf'\b{word}\b', replacement, text, flags=re.IGNORECASE)
    return text


def generate_script(video, signal, baseline, comments, intel, anthropic_key, 
                    is_exact_text=False, length="medium", tone="pro"):
    if not anthropic_key:
        return None

    # Length mapping
    length_map = {
        "short":     "approx 59 seconds (YouTube Short / Vertical)",
        "medium":    "approx 6-10 mins (Standard Documentary)",
        "long":      "approx 15-20 mins (Deep Dive)",
        "resp_short": "EXACTLY 2 mins 50 seconds (Short-form response)",
        "resp_med":   "EXACTLY 6 minutes (Medium response)",
        "resp_long":  "EXACTLY 15 minutes (Full documentary response)",
    }
    length_desc = length_map.get(length, length_map["medium"])

    # Tone mapping
    tone_map = {
        "pro":     "Documentary authority, data-backed, Measured but urgent.",
        "witty":   "Sharp, clever observations, occasional deadpan irony.",
        "funny":   "High energy, comedic timing, absurd juxtapositions, entertaining.",
        "cynical": "No-nonsense, skeptical, 'tell it like it is' attitude.",
    }
    tone_desc = tone_map.get(tone, tone_map["pro"])

    comment_block = "\n".join(
        f'[{c["likes"]} likes] "{c["text"][:250]}"'
        for c in (comments or [])[:60]
    ) or "No comments available."

    angle       = intel.get("my_video_angle", video["title"]) if intel else video["title"]
    hook        = intel.get("hook_idea", "") if intel else ""
    structure   = intel.get("content_structure", []) if intel else []
    audience    = intel.get("target_audience", []) if intel else []
    pulse       = intel.get("comment_pulse", "") if intel else ""
    why         = intel.get("why_spiking", "") if intel else ""
    length_mins = intel.get("recommended_length_mins", 15) if intel else 15
    struct_block = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(structure))
    audience_str = ", ".join(audience)

    if is_exact_text:
        source_text = video["title"]
        prompt = f"""You are a documentary film director and editor.

The user has provided the EXACT TEXT they want as the narration for a video.
CRITICAL: DO NOT REWRITE, SUMMARIZE, OR OMIT ANY PART OF THE TEXT. 
You must use their EXACT text word-for-word as the `narration` field in your JSON output.

Your job is ONLY to:
1. Break the text into logical `sections` (every 100-200 words).
2. The TOTAL aggregation of all `narration` fields in your sections MUST EXACTLY MATCH THE PROVIDED TEXT. 
3. Add visual direction, b-roll keywords, and metadata (titles, thumbnail ideas, etc).
4. Do NOT add any extra narration or commentary of your own.

EXACT NARRATION TEXT PROVIDED:
{source_text}

THE FULL CONTENT PLAN:
Return ONLY valid JSON. No markdown. No text outside the JSON.

{{
  "title": "A compelling title based on the text",
  "title_alternatives": ["Alt 1", "Alt 2", "Alt 3"],
  "thumbnail": {{
    "background": "Exact color and style",
    "main_image": "What to show — be specific",
    "text_overlay": "Max 4 words. Huge. Shocking.",
    "face_expression": "Exact expression if face shown",
    "color_scheme": "Exact colors",
    "mobile_test": "Will this work as a tiny square on a phone? Yes/No and why"
  }},
  "seo_tags": ["tag1","tag2"],
  "description_hook": "First 2 lines",
  "estimated_runtime_mins": {max(1, len(source_text.split()) // 150)},
  "funniest_line": "The best line",
  "hook_score": "Rate the hook 1-10",
  "sections": [
    {{
      "name": "SECTION NAME",
      "timestamp": "0:00",
      "duration_secs": 45,
      "mrbeast_energy": "Pacing note",
      "visual_treatment": "Visual style for this section",
      "pain_addressed": "Fear or desire",
      "narration": "EXACT TEXT SEGMENT HERE — DO NOT REWRITE. WEAVE IN [VISUAL CUE: description] IF NEEDED.",
      "funny_moment": null,
      "open_loop": "Tension created",
      "broll_keywords": ["keyword1", "keyword2", "keyword3"],
      "conversion_note": "Note"
    }}
  ]
}}"""
    else:
        prompt = f"""You are the head writer for the most watched AI and healthcare documentary channel on YouTube.

Your channel sits at the intersection of:
- Breaking AI and tech news
- Healthcare and medical breakthroughs  
- Innovation, money, and unintended consequences

Your writing style combines:
- ENERGY and pacing: {tone_desc}
- MrBeast energy: Every 60-90 seconds must have a 'retention bait' or revelation.
- The Economist authority: Names, numbers, and causal links are mandatory.

TARGET LENGTH: {length_desc}
TONE PROFILE: {tone_desc}

PROJECT ANGLE: {angle}
HOOK STRATEGY: {hook}
AUDIENCE PULSE (from comments): {pulse}
WHY THE TOPIC IS SPIKING: {why}
RECOMMENDED STRUCTURE: 
{struct_block}

CRITICAL RULES:
1. Every script MUST be inherently engaging, hook-driven, and optimized for YouTube retention by default.
2. If tone is 'funny' or 'witty', embed clever metaphors and observational humor.
3. You are writing the COMPLETE word-for-word narration script. 
4. NOT an outline. NOT a summary. NOT bullet points.
5. THE ACTUAL WORDS. EVERY SINGLE WORD.

A human must be able to sit down RIGHT NOW, press record, and read your narration 
word for word with ZERO additional preparation.

If a section is 60 seconds long that is approximately 150 words of narration.
If a section is 2 minutes long that is approximately 300 words of narration.
If the video is 15 minutes total that is approximately 2,250 words of narration.
If the video is 19 minutes total that is approximately 2,850 words of narration.

COUNT YOUR WORDS. If any section has fewer than 100 words of actual narration 
you have FAILED this instruction. Rewrite it until it is complete.

DO NOT write:
- "Narrator explains the background of AI in healthcare..."
- "This section covers the economic implications..."  
- "Introduce the main argument here..."
- "[Explain how AI works]"
- Any bullet points inside the narration field

DO write:
"Last Tuesday a hospital in San Francisco made a decision that shocked the entire 
medical establishment. They fired their radiology department. All of it. Every 
single radiologist. Gone. Not because they were bad at their jobs. They were 
excellent. But because an AI system — one that costs less per month than your 
internet bill — had just outperformed every single one of them on a blind test 
of ten thousand X-rays. [PAUSE] Let that sit for a second."

THAT is what narration looks like. Full sentences. Spoken language. Real words.

CRITICAL — MRBEAST ENERGY RULES:
1. The first 10 seconds must make it IMPOSSIBLE to click away
2. Every 90 seconds — a new revelation, a shocking stat, a tonal shift
3. Stakes must feel PERSONAL to the viewer within 30 seconds
4. Open loops everywhere — always teasing what's coming next
5. The pace never drops. Ever. If a section drags, cut it.
6. End every act with something that makes stopping feel like a mistake

CRITICAL — MONETISATION SAFE:
Never use these words or concepts: {', '.join(BANNED_WORDS[:20])}
Use dramatic but advertiser-safe language throughout.
Frame all sensitive topics around innovation, disruption, transformation.
Healthcare topics: focus on breakthroughs, not suffering.

CRITICAL — CONVERSION OPTIMISED:
- Title must score 9/10 on curiosity gap (makes you NEED to know)
- Thumbnail must work in 0.3 seconds on mobile
- Hook must pass the "3 second test" — would you keep watching?
- CTA must get subscribe + comment + next video simultaneously
- Every section must earn its place — no filler, no padding

THE FULL CONTENT PLAN (not just a script — a complete production package):

VIRAL SIGNAL CONTEXT:
Title         : {video['title']}
Channel       : {video['channel_title']}
Signal        : {signal.get('level','VIRAL')} — {signal.get('multiplier',5)}× above baseline
Views         : {video['views']:,} in {video['age_hours']}h
Our angle     : {angle}
Audience      : {audience_str}
Target length : {length_mins} minutes

WHY IT'S EXPLODING:
{why}

AUDIENCE EMOTION RIGHT NOW:
{pulse}

REAL COMMENTS (use their exact language and fears):
{comment_block}

STRUCTURE TO FOLLOW:
{struct_block}

━━ RETURN A COMPLETE PRODUCTION PACKAGE ━━━━━━━━━━━━━━━━

Return ONLY valid JSON. No markdown. No text outside the JSON.

{{
  "title": "Final title. Must create massive curiosity gap. Under 70 chars. Specific number or shocking claim if possible.",

  "title_alternatives": [
    "Alternative title 1 — more fear-based",
    "Alternative title 2 — more hope-based", 
    "Alternative title 3 — more money-based"
  ],

  "thumbnail": {{
    "background": "Exact color and style",
    "main_image": "What to show — be specific",
    "text_overlay": "Max 4 words. Huge. Shocking.",
    "face_expression": "Exact expression if face shown",
    "color_scheme": "Exact colors",
    "mobile_test": "Will this work as a tiny square on a phone? Yes/No and why",
    "gemini_prompt": "A hyper-detailed image generation prompt for Google Gemini. Include: exact composition, lighting, mood, colors, text placement, style references, aspect ratio 16:9, photorealistic or illustrated style. Must be specific enough that Gemini produces a broadcast-quality YouTube thumbnail on first attempt. Example format: Photorealistic YouTube thumbnail, 16:9 aspect ratio. [describe exactly what is shown]. Dramatic cinematic lighting with [specific colors]. Bold text overlay reading [EXACT TEXT] in [font style] positioned [location]. Background shows [specific scene]. Overall mood: [mood]. Style similar to [reference]. High contrast, eye-catching, works at small size on mobile."
  }},

  "seo_tags": ["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10"],

  "description_hook": "First 2 lines of YouTube description — must hook before Show More button",

  "estimated_runtime_mins": {length_mins},

  "funniest_line": "The single best line in the whole script. The one that ends up in comments.",

  "hook_score": "Rate the hook 1-10 on the 3-second test and explain why",

  "sections": [
    {{
      "name": "HOOK",
      "timestamp": "0:00",
      "duration_secs": 45,
      "mrbeast_energy": "What keeps this from being skippable in this section",
      "visual_treatment": "black_title_card",
      "pain_addressed": "The exact fear or desire activated here",
      "narration": "THE COMPLETE WORD-FOR-WORD NARRATION. Every sentence spoken by the narrator. Nothing left out. Nothing summarised. This field must contain 150-400 words of ACTUAL SPOKEN SCRIPT depending on section length. Natural spoken English — write how a person talks, not how they write. Monetisation safe. Weave in [VISUAL CUE: specific description] markers inline where b-roll should change. Weave in [PAUSE] for dramatic silence. Weave in [TITLE CARD: exact text] for on-screen text moments. Weave in [MUSIC: specific instruction] for music changes. EXAMPLE OF CORRECT FORMAT: Last Tuesday, a hospital in Boston fired their entire radiology department. Not downsized. Fired. All 47 of them. [PAUSE] [VISUAL CUE: empty hospital corridor, no people, fluorescent lights] The AI system that replaced them costs forty dollars a month. [TITLE CARD: $40/MONTH] I want you to sit with that number. Forty dollars. That is less than your Netflix subscription. That is two large pizzas. [PAUSE] And it just made forty-seven highly trained medical professionals redundant. THAT is how you write narration. DO NOT give me anything less than this.",
      "funny_moment": "The specific funny line or observation in this section, or null",
      "open_loop": "What tension this creates that forces them to keep watching",
      "broll_keywords": ["keyword1", "keyword2", "keyword3"],
      "conversion_note": "What makes this section drive watch time specifically"
    }}
  ],

  "fear_hope_money_map": [
    {{
      "fear": "Specific fear from the comments",
      "hope": "The counter-narrative that gives them relief",
      "money": "The financial opportunity or implication",
      "problem_created": "The new problem this technology creates",
      "problem_solved": "The existing problem this technology solves"
    }}
  ],

  "comment_bait": [
    {{
      "timestamp": "timestamp",
      "narration_line": "Exact line that will flood the comments",
      "why": "Psychological mechanism — why this forces a response",
      "expected_comment_type": "What people will actually write"
    }}
  ],

  "cta_narration": "Full word-for-word CTA narration. 30-45 seconds. Natural spoken language. Gets subscribe + comment + next video simultaneously. Funny if possible. Never reads like a sales pitch.",

  "ad_placement_suggestions": [
    "Timestamp and reason — e.g. 4:30 — after the fear section, before the hope reveal. Viewer is hooked and will sit through an ad to get the answer."
  ],

  "youtube_ads_strategy": {{
    "should_run_ads": true,
    "mentor_advice": "Write this as a experienced YouTube mentor talking to a complete beginner. Tone: warm, direct, like a friend who already bought a Lambo from YouTube revenue explaining exactly how you get there too. No jargon. Real numbers. Real steps. Include: when to start ads, how much to spend first, what to look for, when to scale, what mistake beginners make that wastes money.",
    "first_ad_budget": "Exact amount to start with and why",
    "when_to_launch_ads": "Exact timing relative to upload — not vague, specific",
    "target_cpm_to_aim_for": "What CPM means and what number to aim for in this niche",
    "scale_trigger": "The exact signal that tells you to increase budget",
    "biggest_beginner_mistake": "The one mistake that wastes 80 percent of ad spend for new channels",
    "lambo_milestone": "Honest projection — if this video performs and you run ads correctly, what does the revenue look like at 100K, 500K, 1M views in this niche"
  }},

  "sponsorship_angles": [
    "Natural sponsorship integration points for health tech or AI tool brands"
  ],

  "chapter_markers": [
    {{"time": "0:00", "title": "Chapter name"}}
  ],

  "production_notes": [
    "Specific production tip for this video"
  ],

  "banned_words_check": "Confirm: does this script avoid all demonetisation triggers? Yes/No and any flagged phrases",

  "estimated_cpm": "Expected CPM range for this video based on topic and audience",

  "viral_prediction": "Honest assessment — will this video perform? Why?"
}}"""

    result = claude_request(
        model      = CLAUDE_MODEL,
        prompt     = prompt,
        api_key    = anthropic_key,
        max_tokens = 16000,
        timeout    = 120,
        retries    = 2,
        backoff    = 5.0,
    )

    # If API failed, return the error dict as-is
    if result.get("_error"):
        return result

    # Sanitise all narration sections
    for section in result.get("sections", []):
        if section.get("narration"):
            section["narration"] = sanitise_script(section["narration"])
    if result.get("cta_narration"):
        result["cta_narration"] = sanitise_script(result["cta_narration"])

    return result


def format_script_terminal(script):
    """Full terminal output of the production package."""
    if not script:
        return "  (Script generation failed)"
    if script.get("_error"):
        return f"  ⚠ Script error: {script['_error']}"

    W = 65
    lines = [
        "",
        "═" * W,
        f"  📄  {script.get('title', 'Untitled')}",
        "═" * W,
        "",
    ]

    # Alternatives
    alts = script.get("title_alternatives", [])
    if alts:
        lines += ["  📝  TITLE ALTERNATIVES"]
        for a in alts:
            lines.append(f"  → {a}")
        lines.append("")

    # Thumbnail
    th = script.get("thumbnail", {})
    if th:
        lines += [
            "─" * W,
            "  🖼️   THUMBNAIL",
            f"  Text    : {th.get('text_overlay','')}",
            f"  Image   : {th.get('main_image','')}",
            f"  Colors  : {th.get('color_scheme','')}",
            f"  Mobile  : {th.get('mobile_test','')}",
            "",
        ]

    # Key stats
    lines += [
        "─" * W,
        f"  ⏱  Runtime: ~{script.get('estimated_runtime_mins','?')} min",
        f"  💰 Est. CPM: {script.get('estimated_cpm','?')}",
        f"  🎯 Hook score: {script.get('hook_score','?')}",
        f"  😂 Funniest line: \"{script.get('funniest_line','')}\"",
        f"  ✅ Safe: {script.get('banned_words_check','')}",
        "",
    ]

    # Fear/Hope/Money map
    fhm = script.get("fear_hope_money_map", [])
    if fhm:
        lines += ["─" * W, "  💡  FEAR → HOPE → MONEY → CONSEQUENCES"]
        for item in fhm:
            lines += [
                f"  FEAR    : {item.get('fear','')}",
                f"  HOPE    : {item.get('hope','')}",
                f"  MONEY   : {item.get('money','')}",
                f"  CREATES : {item.get('problem_created','')}",
                f"  SOLVES  : {item.get('problem_solved','')}",
                "",
            ]

    # Script sections
    lines += ["─" * W, "  🎬  FULL SCRIPT"]
    for section in script.get("sections", []):
        lines += [
            "",
            f"  [{section.get('timestamp','')}] {section.get('name','').upper()}",
            f"  Energy: {section.get('mrbeast_energy','')}",
            "  " + "·" * (W - 4),
            "",
        ]
        for para in section.get("narration", "").split("\n"):
            if para.strip():
                words = para.split()
                line  = "  "
                for word in words:
                    if len(line) + len(word) + 1 > 67:
                        lines.append(line)
                        line = "  " + word + " "
                    else:
                        line += word + " "
                if line.strip():
                    lines.append(line)
            else:
                lines.append("")
        if section.get("open_loop"):
            lines += ["", f"  → {section['open_loop']}"]
        lines.append("")

    # Comment bait
    cb = script.get("comment_bait", [])
    if cb:
        lines += ["─" * W, "  💬  COMMENT BAIT"]
        for m in cb:
            lines += [
                f"  {m.get('timestamp','')} — \"{m.get('narration_line','')}\"",
                f"  Expected: {m.get('expected_comment_type','')}",
                "",
            ]

    # CTA
    if script.get("cta_narration"):
        lines += ["─" * W, "  📢  CTA", "", f"  {script['cta_narration']}", ""]

    # Sponsorship
    sp = script.get("sponsorship_angles", [])
    if sp:
        lines += ["─" * W, "  💼  SPONSORSHIP ANGLES"]
        for s in sp:
            lines.append(f"  › {s}")
        lines.append("")

    # Viral prediction
    if script.get("viral_prediction"):
        lines += ["─" * W, f"  🔮  {script['viral_prediction']}", ""]

    lines += ["═" * W, ""]
    return "\n".join(lines)


def format_script_telegram(script, video):
    """Viral Response Package for Telegram."""
    if not script or script.get("_error"):
        return None

    fhm  = script.get("fear_hope_money_map", [{}])
    cb   = script.get("comment_bait", [{}])
    alts = script.get("title_alternatives", [])

    # Build the message
    msg = (
        f"🧙 <b>SORCERER — VIRAL RESPONSE</b>\n"
        f"─────────────────────────\n\n"

        f"🎯 <b>RESPONSE ANGLE</b>\n"
        f"<b>{script.get('title','')}</b>\n\n"
    )

    if alts:
        msg += "<b>Alternative Angles:</b>\n"
        for a in alts:
            msg += f"  • {a}\n"
        msg += "\n"

    msg += (
        f"⏱ Length: ~{script.get('estimated_runtime_mins','?')} min\n"
        f"🎣 Hook Score: {script.get('hook_score','?')}/10\n"
        f"😂 <b>Punchline:</b>\n"
        f"<i>\"{script.get('funniest_line','')}\"</i>\n\n"
    )

    # Fear/Hope/Money
    if fhm and fhm[0]:
        item = fhm[0]
        msg += (
            f"💡 <b>FEAR → HOPE → MONEY</b>\n"
            f"😰 {item.get('fear','')}\n"
            f"✨ {item.get('hope','')}\n"
            f"💰 {item.get('money','')}\n"
            f"⚡ Creates: {item.get('problem_created','')}\n"
            f"✅ Solves: {item.get('problem_solved','')}\n\n"
        )

    # Hook
    sections = script.get("sections", [])
    if sections:
        hook_section = sections[0]
        narration_preview = hook_section.get("narration","")[:400]
        msg += (
            f"🎤 <b>HOOK (first 45 seconds)</b>\n"
            f"<i>{narration_preview}...</i>\n\n"
        )

    # Comment bait
    if cb and cb[0]:
        msg += (
            f"💬 <b>COMMENT BAIT</b>\n"
            f"\"{cb[0].get('narration_line','')}\"\n"
            f"<i>{cb[0].get('expected_comment_type','')}</i>\n\n"
        )

    # Sponsorship integration point (sponsorship_angles is a list)
    sp = script.get("sponsorship_angles", [])
    if sp:
        msg += f"💼 <b>SPONSORSHIP ANGLE</b>\n{sp[0]}\n\n"

    # Strategic Insight (Ads/Growth)
    ads = script.get("youtube_ads_strategy", {})
    if ads:
        msg += (
            f"📈 <b>STRATEGIC INSIGHT</b>\n"
            f"─────────────────────────\n"
            f"<i>{ads.get('mentor_advice','')}</i>\n\n"
            f"💵 Recommended Budget: {ads.get('first_ad_budget','')}\n"
            f"⏰ Launch Timing: {ads.get('when_to_launch_ads','')}\n"
            f"⚠️ Common Mistake: {ads.get('biggest_beginner_mistake','')}\n\n"
        )

    # Full script sections
    sections = script.get("sections", [])
    if sections:
        msg += "📜 <b>FULL SCRIPT</b>\n─────────────────────────\n\n"
        for section in sections:
            narration = section.get("narration", "")
            # Send each section
            section_msg = (
                f"🎬 <b>[{section.get('timestamp','')}] {section.get('name','').upper()}</b>\n"
                f"<i>~{section.get('duration_secs',0)}s</i>\n\n"
                f"{narration}"
            )
            msg += section_msg + "\n\n"

    # Viral prediction
    if script.get("viral_prediction"):
        msg += f"🔮 <b>{script['viral_prediction']}</b>\n\n"

    msg += (
        f"✅ Monetisation safe: {script.get('banned_words_check','')}\n\n"
        f"<a href='https://youtube.com/watch?v={video.get('id','')}'>"
        f"Watch competitor video →</a>"
    )

    return msg


def save_script(script, video, output_dir):
    """Save complete production package as markdown."""
    if not script or script.get("_error"):
        return None

    from pathlib import Path
    title    = script.get("title", "script").replace(" ", "_").replace("/", "-")[:50]
    ts       = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"{ts}_{title}.md"
    filepath = Path(output_dir) / "scripts" / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)

    th  = script.get("thumbnail", {})
    fhm = script.get("fear_hope_money_map", [])

    md = f"""# Viral Response: {script.get('title', 'Untitled')}

> SORCERER · {datetime.now().strftime('%Y-%m-%d %H:%M')}
> Source: [{video['title']}](https://youtube.com/watch?v={video['id']})
> Runtime: ~{script.get('estimated_runtime_mins','?')} min

---

## Title Alternatives
"""
    for a in script.get("title_alternatives", []):
        md += f"- {a}\n"

    md += f"""
## Thumbnail
- **Text:** {th.get('text_overlay','')}
- **Image:** {th.get('main_image','')}
- **Colors:** {th.get('color_scheme','')}
- **Mobile test:** {th.get('mobile_test','')}

## SEO Tags
`{' · '.join(script.get('seo_tags', []))}`

## Description Hook
{script.get('description_hook','')}

---

## 😂 Funniest Line
> "{script.get('funniest_line','')}"

## Hook Score
{script.get('hook_score','')}

## Monetisation
{script.get('banned_words_check','')} · Est. CPM: {script.get('estimated_cpm','')}

---

## Fear → Hope → Money → Consequences

"""
    for item in fhm:
        md += f"**Fear:** {item.get('fear','')}\n"
        md += f"**Hope:** {item.get('hope','')}\n"
        md += f"**Money:** {item.get('money','')}\n"
        md += f"**Problem created:** {item.get('problem_created','')}\n"
        md += f"**Problem solved:** {item.get('problem_solved','')}\n\n"

    md += "---\n\n## Full Script\n\n"
    for section in script.get("sections", []):
        md += f"### [{section.get('timestamp','')}] {section.get('name','').upper()}\n"
        md += f"*~{section.get('duration_secs',0)}s*\n\n"
        md += f"**MrBeast energy check:** {section.get('mrbeast_energy','')}\n\n"
        md += f"{section.get('narration','')}\n\n"
        if section.get("open_loop"):
            md += f"> **→ Open loop:** {section['open_loop']}\n\n"
        md += "---\n\n"

    cb = script.get("comment_bait", [])
    if cb:
        md += "## Comment Bait\n\n"
        for m in cb:
            md += f"**{m.get('timestamp','')}** → *\"{m.get('narration_line','')}\"*\n"
            md += f"Expected: {m.get('expected_comment_type','')}\n\n"

    md += f"## CTA\n\n{script.get('cta_narration','')}\n\n"

    sp = script.get("sponsorship_angles", [])
    if sp:
        md += "## Sponsorship Angles\n\n"
        for s in sp:
            md += f"- {s}\n"

    md += f"\n## Viral Prediction\n\n{script.get('viral_prediction','')}\n\n"

    # Strategic Insight
    ads = script.get("youtube_ads_strategy", {})
    if ads:
        md += "## 📈 Strategic Insight\n\n"
        md += f"{ads.get('mentor_advice','')}\n\n"
        md += f"**Recommended budget:** {ads.get('first_ad_budget','')}\n"
        md += f"**Launch timing:** {ads.get('when_to_launch_ads','')}\n"
        md += f"**Common mistake:** {ads.get('biggest_beginner_mistake','')}\n\n"

    markers = script.get("chapter_markers", [])
    if markers:
        md += "## YouTube Chapters\n\n"
        for m in markers:
            md += f"`{m.get('time','')}` {m.get('title','')}\n"

    notes = script.get("production_notes", [])
    if notes:
        md += "\n## Production Notes\n\n"
        for n in notes:
            md += f"- {n}\n"

    filepath.write_text(md, encoding="utf-8")
    return str(filepath)


# Keep old names for compatibility
save_script_file = save_script


def generate_screen_assets(video, comments, anthropic_key, num_shots=7):
    """
    Identify the most visually valuable moments in the source video.

    Returns a list of {"timestamp_secs": int, "timestamp_str": "MM:SS",
    "reason": str, "what_to_capture": str, "url": str}

    These are screenshot targets — specific moments the user can open and
    pause to grab for use in their own low-resource response video.
    """
    if not anthropic_key:
        return None

    vid_id = video.get("id", "")
    duration_mins = video.get("duration_mins", 10)
    duration_secs = int(duration_mins * 60)

    comment_block = "\n".join(
        f'[{c["likes"]} likes] "{c["text"][:200]}"'
        for c in (comments or [])[:30]
    ) or "No comments available."

    prompt = f"""You are helping a low-resource solo creator build a response video to this high-performing video.
They cannot afford original footage, animations, or stock video.
Their strategy: screenshot specific moments from the source video to use as B-roll clips in their own video.

VIDEO:
Title: {video['title']}
Channel: {video['channel_title']}
Duration: {duration_mins:.0f} minutes ({duration_secs} seconds)
Views: {video.get('views', 0):,}

TOP COMMENTS (audience reactions):
{comment_block}

YOUR TASK:
Identify exactly {num_shots} timestamps in the source video that would be most useful as visual assets.
For each, identify a moment that shows:
- A key data point, chart, or statistic being displayed
- A dramatic or surprising visual moment audiences reacted to
- A "before/after" or comparison frame
- The host making a key claim or reveal
- A moment that provokes the reaction "I need to respond to this"

Return a JSON array ONLY, no prose:
[
  {{
    "timestamp_secs": <integer seconds from video start>,
    "timestamp_str": "<MM:SS format>",
    "reason": "<1-sentence: why this is a useful asset>",
    "what_to_capture": "<exactly what will be visible on screen at this moment>"
  }}
]

Timestamps must be between 0 and {duration_secs}. Space them out across the video."""

    try:
        raw = claude_request(prompt, anthropic_key, model=CLAUDE_MODEL, max_tokens=1500)
        if not raw or raw.get("_error"):
            return None

        # raw is already a dict from claude_request — but here we expect a list
        # We need the raw string instead
        return raw  # claude_request returns parsed JSON, which may already be a list
    except Exception:
        return None


def _claude_screen_request(prompt, anthropic_key):
    """Make a raw Claude request and return the parsed JSON list."""
    import requests as _req
    headers = {
        "x-api-key": anthropic_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": 1500,
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        r = _req.post("https://api.anthropic.com/v1/messages", headers=headers, json=body, timeout=60)
        r.raise_for_status()
        raw_text = r.json()["content"][0]["text"].strip()
        raw_text = raw_text.lstrip("```json").lstrip("```").rstrip("```").strip()
        # Find JSON array in the text
        start = raw_text.find("[")
        end = raw_text.rfind("]") + 1
        if start >= 0 and end > start:
            import json
            return json.loads(raw_text[start:end])
    except Exception:
        pass
    return None


def get_screen_assets(video, comments, anthropic_key, num_shots=7):
    """
    Main entry point: get visually useful screenshot targets.
    Returns a list of timestamped moments with YT deep-links.
    """
    vid_id = video.get("id", "")
    duration_mins = video.get("duration_mins", 10)
    duration_secs = int(duration_mins * 60)

    comment_block = "\n".join(
        f'[{c["likes"]} likes] "{c["text"][:200]}"'
        for c in (comments or [])[:30]
    ) or "No comments available."

    prompt = f"""You are helping a low-resource solo creator build a response video to this viral video.
They cannot record original footage. They will screenshot specific moments from the source video to use as visual evidence and B-roll in their own response.

VIDEO:
Title: {video['title']}
Channel: {video['channel_title']}
Duration: {duration_mins:.0f} minutes total ({duration_secs} seconds)
Views: {video.get('views', 0):,}

TOP COMMENTS (audience sentiment):
{comment_block}

TASK: Identify {num_shots} specific timestamps to screenshot. Prioritize:
1. Moments where a key claim, stat, or data is shown on screen
2. Visual reveals / "wait what?" moments the audience reacted to
3. Charts, graphs, or comparisons being presented
4. The host making their strongest argument
5. Moments that directly provoke a response from a competitor

Return ONLY a JSON array. No extra text. No markdown.
[
  {{
    "timestamp_secs": <int>,
    "timestamp_str": "<MM:SS>",
    "reason": "<why this screenshot is useful>",
    "what_to_capture": "<what is literally visible on screen>",
    "crop_hint": "<which part of the frame to crop: e.g. 'top-left quadrant showing the stat', 'full frame', 'bottom third with the caption', 'right half showing the chart'>"
  }}
]

All timestamps must be between 0 and {duration_secs} seconds. Spread them across the full video."""

    shots = _claude_screen_request(prompt, anthropic_key)

    if not shots or not isinstance(shots, list):
        return None

    # Attach YouTube deep-links
    for shot in shots:
        t = shot.get("timestamp_secs", 0)
        shot["url"] = f"https://youtube.com/watch?v={vid_id}&t={t}s"

    return shots


def format_screen_assets_telegram(shots, video):
    """Format the screenshot targets for Telegram."""
    if not shots:
        return "❌ Could not identify screenshot targets."

    msg = (
        f"🖼 <b>Screen Assets — {len(shots)} Key Moments</b>\n"
        f"<i>Source: {video['title'][:50]}</i>\n\n"
        f"<i>Open each link → pause → screenshot → crop as indicated</i>\n"
        f"{'─' * 25}\n\n"
    )

    for i, shot in enumerate(shots, 1):
        crop = shot.get('crop_hint', 'full frame')
        msg += (
            f"<b>{i}. {shot['timestamp_str']}</b> — {shot['reason']}\n"
            f"📌 <i>{shot['what_to_capture']}</i>\n"
            f"✂️ Crop: <code>{crop}</code>\n"
            f"<a href='{shot['url']}'>→ Jump to {shot['timestamp_str']}</a>\n\n"
        )

    msg += "<i>Crop tightly around the key element. Use in your B-roll or as a reaction clip.</i>"
    return msg
format_script_terminal = format_script_terminal
