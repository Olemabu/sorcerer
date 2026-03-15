"""
SORCERER — Script Writer (Documentary Edition)
================================================
Writes scripts that are:
  - Gripping: open loops, tension, stakes established in 10 seconds
  - Entertaining: unexpected analogies, rhythm, momentum
  - FUNNY: dark humor, absurdist comparisons, self-aware wit
    The kind of funny that makes people rewatch a line and
    quote it in comments. Not cringe. Not try-hard.
    The Kurzgesagt meets John Oliver meets actual documentary.

Claude Opus only. Script quality is the product.
"""

import json
import requests

CLAUDE_MODEL  = "claude-opus-4-5"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


def generate_script(video, signal, baseline, comments, intel, anthropic_key):
    if not anthropic_key:
        return None

    comment_block = "\n".join(
        f'[{c["likes"]} likes] "{c["text"][:250]}"'
        for c in (comments or [])[:60]
    ) or "No comments available."

    angle         = intel.get("my_video_angle", video["title"]) if intel else video["title"]
    hook          = intel.get("hook_idea", "") if intel else ""
    structure     = intel.get("content_structure", []) if intel else []
    audience      = intel.get("target_audience", []) if intel else []
    pulse         = intel.get("comment_pulse", "") if intel else ""
    why           = intel.get("why_spiking", "") if intel else ""
    length_mins   = intel.get("recommended_length_mins", 15) if intel else 15

    struct_block  = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(structure))
    audience_str  = ", ".join(audience)

    prompt = f"""You are the writer behind the most entertaining, funny, and genuinely gripping documentary channel on YouTube.

Your style:
- Kurzgesagt's visual storytelling instincts
- John Oliver's comedic timing and absurdist analogies
- MKBHD's authority and directness
- The Economist's wit without the stuffiness
- A stand-up comedian who happens to know everything about tech and business

You write narration scripts — no host on camera, just voice over documentary footage.
The script must be READ ALOUD. Write for the ear, not the eye.
Short sentences when building tension. Longer ones when explaining.
Rhythm matters. Pacing matters. The occasional one-liner that makes someone choke on their coffee matters.

WHAT'S GOING VIRAL RIGHT NOW:
Title         : {video['title']}
Channel       : {video['channel_title']}
Signal        : {signal.get('level','VIRAL')} — {signal.get('multiplier',5)}× above baseline
Age           : {video['age_hours']}h old · {video['views']:,} views
Target length : {length_mins} minutes of narration
Our angle     : {angle}
Audience      : {audience_str}

WHY PEOPLE ARE LOSING THEIR MINDS OVER THIS:
{why}

WHAT THE COMMENTS ARE ACTUALLY SAYING:
{pulse}

TOP COMMENTS (mine these for the exact language and fears of the audience):
{comment_block}

STRATEGIC STRUCTURE:
{struct_block}

HOOK DIRECTION:
{hook}

━━ WRITING RULES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HUMOR RULES (mandatory — this is what separates us):
1. Funny through SPECIFICITY, not jokes. "A startup in San Francisco replaced their entire HR department with a $40/month AI" is funnier than any joke.
2. Absurdist comparisons that are also accurate. If AI is taking jobs, compare it to something historically parallel but ridiculous.
3. Dry delivery. State the insane thing completely deadpan. Let the audience do the work.
4. ONE genuine laugh-out-loud moment per section. Not a punchline. A perfect observation.
5. Dark humor is fine. Gallows humor about tech disruption is our brand. 
6. Never explain the joke. Never say "which is ironic" or "if you can believe it."
7. The funniest line in any section should be the LAST line before the next section starts.

GRIP RULES (mandatory):
1. Open with something that sounds wrong. Make them need to know why it's right.
2. Every section ends with a question or statement that makes stopping feel impossible.
3. Plant a "wait for it" in the first 60 seconds that pays off at minute 10+.
4. State the stakes early. Make it personal. "This affects you" not "this affects society."
5. Pattern interrupt every 90 seconds — sudden tonal shift, shocking stat, unexpected silence cue.

DOCUMENTARY NARRATION RULES:
1. Write [VISUAL CUE: description] markers so the editor knows what to cut to.
2. [MUSIC: instruction] markers at key emotional shifts.
3. [PAUSE] for dramatic effect — the silence is part of the script.
4. [TITLE CARD: text] for on-screen text moments.
5. Narration reads at roughly 150 words per minute. A 15-minute video = ~2,250 words of narration.

━━ OUTPUT FORMAT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return ONLY valid JSON. No markdown. No text outside the JSON.

{{
  "title": "Final video title. Punchy. Specific. Slightly threatening.",

  "thumbnail_direction": "Exact description. What image. What text overlay. What expression if face shown. What color. Be specific enough that a designer can execute without asking questions.",

  "seo_tags": ["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10"],

  "estimated_runtime_mins": {length_mins},

  "funniest_line": "The single best line in the whole script. The one that will end up in comments.",

  "sections": [
    {{
      "name": "HOOK",
      "timestamp": "0:00",
      "duration_secs": 50,
      "visual_treatment": "black_title_card",
      "pain_addressed": "The specific fear or curiosity this activates",
      "narration": "The full word-for-word narration. Natural spoken language. No corporate speak. Include [VISUAL CUE: ...], [MUSIC: ...], [PAUSE], [TITLE CARD: ...] markers throughout. The funny line if this section has one.",
      "funny_moment": "The specific funny line or observation in this section, or null",
      "open_loop": "What question or tension this section creates that the next section must resolve",
      "broll_keywords": ["keyword1", "keyword2", "keyword3"]
    }}
  ],

  "comment_bait": [
    {{
      "timestamp": "approximate timestamp",
      "narration_line": "The exact line that will trigger mass comments",
      "why": "The psychological mechanic — why this line forces a response"
    }}
  ],

  "cta_narration": "The full CTA narration. 30-45 seconds. Gets subscribe + comment + next video. Sounds human, not like a YouTube tutorial. Can be slightly self-deprecating or funny.",

  "pain_profit_map": [
    {{
      "pain": "Specific audience fear from the comments",
      "insight": "The reframe the video delivers",
      "profit": "What they leave with"
    }}
  ],

  "production_notes": [
    "Specific note for this video's production",
    "Another specific note",
    "Another"
  ],

  "chapter_markers": [
    {{"time": "0:00", "title": "Chapter name"}},
    {{"time": "2:30", "title": "Chapter name"}}
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
                "max_tokens": 9000,
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=120,
        )
        r.raise_for_status()
        raw = r.json()["content"][0]["text"].strip()
        raw = raw.lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(raw)

    except json.JSONDecodeError as e:
        return {"_error": f"JSON parse failed: {e}", "_raw": raw[:500]}
    except Exception as e:
        return {"_error": str(e)}


def save_script(script, video, output_dir):
    """Save as clean markdown — open in any teleprompter or editor."""
    import os
    from pathlib import Path
    from datetime import datetime

    if not script or script.get("_error"):
        return None

    title    = script.get("title", "script").replace(" ", "_").replace("/", "-")[:50]
    ts       = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"{ts}_{title}.md"
    filepath = Path(output_dir) / "scripts" / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)

    funniest = script.get("funniest_line", "")

    md = f"""# {script.get('title', 'Untitled')}

> SORCERER · {datetime.now().strftime('%Y-%m-%d %H:%M')}
> Source: [{video['title']}](https://youtube.com/watch?v={video['id']}) — {video['channel_title']}
> Runtime: ~{script.get('estimated_runtime_mins', '?')} minutes

---

> 💀 **Funniest line:** *"{funniest}"*

---

## Thumbnail
{script.get('thumbnail_direction', '—')}

## SEO Tags
`{' · '.join(script.get('seo_tags', []))}`

---

## Pain → Profit Map

"""
    for item in script.get("pain_profit_map", []):
        md += f"**Pain:** {item.get('pain','')}\n"
        md += f"**Insight:** {item.get('insight','')}\n"
        md += f"**Profit:** {item.get('profit','')}\n\n"

    md += "---\n\n## Script\n\n"

    for section in script.get("sections", []):
        funny = section.get("funny_moment")
        md += f"### [{section.get('timestamp','')}] {section.get('name','').upper()}\n"
        md += f"*~{section.get('duration_secs',0)}s · {section.get('pain_addressed','')}*\n\n"
        md += f"{section.get('narration','')}\n\n"
        if funny:
            md += f"> 😂 **Funny moment:** *\"{funny}\"*\n\n"
        if section.get("open_loop"):
            md += f"> **→ Open loop:** {section['open_loop']}\n\n"
        md += "---\n\n"

    cb = script.get("comment_bait", [])
    if cb:
        md += "## Comment Bait Moments\n\n"
        for m in cb:
            md += f"**{m.get('timestamp','')}** → *\"{m.get('narration_line','')}\"*\n"
            md += f"_{m.get('why','')}_\n\n"

    md += f"## CTA\n\n{script.get('cta_narration','')}\n\n"

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

def save_script_file(script, video, output_dir):
    """Alias for save_script - keeps sorcerer.py import working."""
    return save_script(script, video, output_dir)


def format_script_terminal(script):
    """Return a terminal-friendly summary of the generated script."""
    if not script or script.get("_error"):
        err = (script or {}).get("_error", "unknown")
        return "  [Script error: " + str(err) + "]"
    out = []
    out.append("")
    out.append("  " + "=" * 60)
    out.append("  SCRIPT: " + script.get("title", "Untitled")[:54])
    out.append("  " + "=" * 60)
    funny = script.get("funniest_line", "")
    if funny:
        out.append("  Best line: " + funny[:54])
        out.append("  " + "-" * 60)
    for s in script.get("sections", []):
        ts = s.get("timestamp", "")
        name = s.get("name", "")
        out.append("  [" + ts + "] " + name)
    out.append("  " + "-" * 60)
    runtime = str(script.get("estimated_runtime_mins", "?"))
    tags = ", ".join(script.get("seo_tags", [])[:4])
    out.append("  ~" + runtime + " mins | " + tags[:40])
    out.append("  " + "=" * 60)
    out.append("")
    return "\n".join(out)