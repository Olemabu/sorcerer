"""
SORCERER — Visual Director
===========================
Reads the script and makes shot-by-shot decisions.

For each section it decides:
  - Which b-roll keywords to search for
  - How many cuts to make
  - Whether to use a title card, lower third, stat counter, etc.
  - What the visual tone should be

Also handles the Kling AI calls for hero cinematic shots
where stock footage won't cut it.

Kling AI: ~$0.14 per 5-second clip
Use sparingly — 2-3 hero shots per video max.
Everything else comes from Pexels (free).
"""

import json
import requests
import time
from pathlib import Path

CLAUDE_MODEL  = "claude-sonnet-4-6"   # Sonnet is fine for this — it's structured output
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
PEXELS_API    = "https://api.pexels.com/videos"
KLING_API     = "https://api.klingai.com/v1"


# ── Visual treatment plan ───────────────────────────────────────────────────
def build_shot_list(script, anthropic_key, log_fn=print):
    """
    Ask Claude to build a complete shot list for the video.
    Returns list of shot dicts with broll queries and timing.
    """
    if not anthropic_key:
        return _fallback_shot_list(script)

    sections     = script.get("sections", [])
    section_data = json.dumps([{
        "name":       s.get("name"),
        "timestamp":  s.get("timestamp"),
        "duration":   s.get("duration_secs"),
        "treatment":  s.get("visual_treatment"),
        "narration":  s.get("narration","")[:300],
        "keywords":   s.get("broll_keywords", []),
        "funny":      s.get("funny_moment"),
    } for s in sections], indent=2)

    prompt = f"""You are a documentary film director and editor.

You have a script for a cinematic documentary YouTube video.
Your job: build a complete shot list — what footage to show during each section.

For each section, specify:
1. Pexels search queries (free stock footage) — specific, visual, searchable
2. Kling AI prompts (for 1-3 hero shots that need to look cinematic and original)
3. Number of cuts within the section
4. Any title cards or text overlays needed

STYLE GUIDE:
- Cinematic. Dark. Dramatic. Occasional ironic visual contrast for humor moments.
- Humor sections: use unexpected visual juxtaposition (e.g. talking about AI taking over → cut to a toaster)
- Stats: tight close-ups, numbers filling screen, fast cut
- Tension: fast cuts, dark footage, urban/tech environments
- Prediction: slow atmospheric shots, empty spaces, future-feeling
- Hook: minimal, almost nothing, let the narration breathe

SECTIONS:
{section_data}

Return ONLY valid JSON. No markdown. No preamble.

{{
  "shots": [
    {{
      "section_name": "HOOK",
      "timestamp_start": "0:00",
      "duration_secs": 50,
      "visual_treatment": "black_title_card",
      "pexels_queries": [
        {{"query": "specific search term", "duration_secs": 8, "notes": "what to look for in results"}},
        {{"query": "another search term", "duration_secs": 6, "notes": "description"}}
      ],
      "kling_shots": [
        {{
          "prompt": "Hyper-detailed cinematic shot description for AI video generation. Include lighting, mood, camera movement.",
          "duration_secs": 5,
          "placement": "opening shot"
        }}
      ],
      "title_cards": [
        {{"text": "On-screen text", "timing": "0:00", "duration_secs": 2.5, "style": "main_title"}}
      ],
      "lower_thirds": [],
      "cut_count": 3,
      "humor_visual": null,
      "color_note": "extra dark, minimal light"
    }}
  ]
}}

Only include kling_shots for the 2-3 most visually important moments.
Everything else uses pexels. Kling is expensive — use it for the shots that will make people screenshot the video."""

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
            timeout=45,
        )
        r.raise_for_status()
        raw = r.json()["content"][0]["text"].strip()
        raw = raw.lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(raw)
        return data.get("shots", _fallback_shot_list(script))

    except Exception as e:
        log_fn(f"  ⚠ Shot list generation failed: {e} — using fallback")
        return _fallback_shot_list(script)


def _fallback_shot_list(script):
    """Basic shot list from script's own broll_keywords."""
    shots = []
    for section in script.get("sections", []):
        keywords = section.get("broll_keywords", ["technology", "city", "future"])
        shots.append({
            "section_name":  section.get("name"),
            "timestamp_start": section.get("timestamp", "0:00"),
            "duration_secs": section.get("duration_secs", 60),
            "visual_treatment": section.get("visual_treatment", "slow_broll_narration"),
            "pexels_queries": [{"query": kw, "duration_secs": 6, "notes": ""} for kw in keywords[:3]],
            "kling_shots":   [],
            "title_cards":   [],
            "lower_thirds":  [],
            "cut_count":     3,
        })
    return shots


# ── Pexels b-roll fetcher ───────────────────────────────────────────────────
def fetch_broll(query, pexels_key, duration_target_secs=6, per_page=5):
    """
    Search Pexels for b-roll footage matching the query.
    Returns list of video dicts with download URLs.
    """
    if not pexels_key:
        return []

    try:
        r = requests.get(
            f"{PEXELS_API}/search",
            headers={"Authorization": pexels_key},
            params={
                "query":    query,
                "per_page": per_page,
                "orientation": "landscape",
                "size": "medium",
            },
            timeout=15,
        )
        r.raise_for_status()
        videos = r.json().get("videos", [])

        results = []
        for video in videos:
            # Find the best quality file close to our target duration
            files = sorted(
                video.get("video_files", []),
                key=lambda f: abs(video.get("duration", 10) - duration_target_secs)
            )

            # Prefer HD files
            hd_files = [f for f in files if f.get("quality") in ("hd", "sd")]
            best     = hd_files[0] if hd_files else (files[0] if files else None)

            if best:
                results.append({
                    "id":          video["id"],
                    "url":         best["link"],
                    "width":       best.get("width", 1920),
                    "height":      best.get("height", 1080),
                    "duration":    video.get("duration", 10),
                    "query":       query,
                    "photographer": video.get("user", {}).get("name", ""),
                })

        return results

    except Exception:
        return []


def download_broll(url, output_path, log_fn=print):
    """Download a Pexels video file."""
    try:
        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        log_fn(f"  ⚠ Download failed: {e}")
        return False


# ── Kling AI hero shots ─────────────────────────────────────────────────────
def generate_kling_shot(prompt, kling_key, duration_secs=5, log_fn=print):
    """
    Generate an AI cinematic shot using Kling AI.
    Returns video URL or None.

    Cost: ~$0.14 per 5-second clip
    Use for 2-3 hero shots per video only.
    """
    if not kling_key:
        log_fn("  ⚠ No KLING_API_KEY — skipping AI shot generation")
        return None

    try:
        log_fn(f"  🎬 Generating Kling shot: {prompt[:60]}...")

        # Submit generation job
        r = requests.post(
            f"{KLING_API}/videos/text2video",
            headers={
                "Authorization": f"Bearer {kling_key}",
                "Content-Type":  "application/json",
            },
            json={
                "prompt":          prompt,
                "duration":        duration_secs,
                "aspect_ratio":    "16:9",
                "mode":            "std",
                "camera_movement": "subtle_zoom",
            },
            timeout=30,
        )
        r.raise_for_status()
        task_id = r.json().get("data", {}).get("task_id")

        if not task_id:
            return None

        # Poll for completion
        for attempt in range(40):
            time.sleep(8)
            status_r = requests.get(
                f"{KLING_API}/videos/text2video/{task_id}",
                headers={"Authorization": f"Bearer {kling_key}"},
                timeout=15,
            )
            status_r.raise_for_status()
            data   = status_r.json().get("data", {})
            status = data.get("task_status")

            if status == "succeed":
                works = data.get("task_result", {}).get("videos", [])
                if works:
                    return works[0].get("url")
                return None
            elif status == "failed":
                log_fn("  ⚠ Kling generation failed")
                return None

        log_fn("  ⚠ Kling generation timed out")
        return None

    except Exception as e:
        log_fn(f"  ⚠ Kling error: {e}")
        return None


# ── Fetch all footage for a video ──────────────────────────────────────────
def fetch_all_footage(shot_list, pexels_key, kling_key, output_dir, log_fn=print):
    """
    Download all b-roll and generate all Kling hero shots.

    Returns list of footage items with local file paths.
    """
    footage_dir = Path(output_dir) / "footage"
    footage_dir.mkdir(parents=True, exist_ok=True)

    footage_map = []   # indexed by section

    for shot in shot_list:
        section_footage = {
            "section_name":    shot["section_name"],
            "timestamp_start": shot.get("timestamp_start", "0:00"),
            "duration_secs":   shot.get("duration_secs", 60),
            "visual_treatment": shot.get("visual_treatment"),
            "title_cards":     shot.get("title_cards", []),
            "lower_thirds":    shot.get("lower_thirds", []),
            "clips":           [],
        }

        # Pexels b-roll
        for pq in shot.get("pexels_queries", []):
            query    = pq.get("query", "")
            dur      = pq.get("duration_secs", 6)
            results  = fetch_broll(query, pexels_key, duration_target_secs=dur)

            if results:
                video    = results[0]
                filename = footage_dir / f"{shot['section_name']}_{query[:20].replace(' ','_')}.mp4"

                log_fn(f"  📹 Downloading: {query}...", )
                ok = download_broll(video["url"], str(filename), log_fn)
                if ok:
                    section_footage["clips"].append({
                        "type":     "broll",
                        "file":     str(filename),
                        "duration": dur,
                        "query":    query,
                        "source":   "pexels",
                    })
                    log_fn(" ✓")
                else:
                    log_fn(" ✗")

            time.sleep(0.2)  # Rate limit

        # Kling hero shots (expensive — limited)
        for ks in shot.get("kling_shots", []):
            if not kling_key:
                continue
            prompt   = ks.get("prompt", "")
            dur      = ks.get("duration_secs", 5)
            filename = footage_dir / f"{shot['section_name']}_kling_{len(section_footage['clips'])}.mp4"

            url = generate_kling_shot(prompt, kling_key, dur, log_fn)
            if url:
                ok = download_broll(url, str(filename), log_fn)
                if ok:
                    section_footage["clips"].append({
                        "type":     "kling",
                        "file":     str(filename),
                        "duration": dur,
                        "prompt":   prompt,
                        "source":   "kling",
                    })

        footage_map.append(section_footage)

    return footage_map
