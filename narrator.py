"""
SORCERER — Narrator
====================
Converts script narration to audio using Microsoft Edge TTS.

Features:
  - Uses Edge TTS natural voices (Free, no API key required)
  - Renders each script section separately for precise timing
  - Handles [PAUSE] markers by inserting silence
  - Strips visual cue markers before sending to TTS
  - Concatenates all sections into one master narration audio
  - Returns per-section audio files + timing data for compositor

Setup:
  1. No setup required! `edge-tts` python package is completely free.
  2. Set EDGE_TTS_VOICE=en-US-ChristopherNeural in .env to choose voice.
"""

import os
import re
import time
from pathlib import Path

# Best models for documentary narration
DEFAULT_VOICE   = "en-US-ChristopherNeural"


# Pause durations
PAUSE_DURATIONS = {
    "[PAUSE]":        0.8,   # Standard dramatic pause
    "[LONG PAUSE]":   1.5,   # Extended silence
    "[BEAT]":         0.4,   # Quick beat
}


def clean_narration(text):
    """
    Strip visual cues and production markers from narration text.
    Keep [PAUSE] markers for silence insertion.
    """
    # Remove visual cues
    text = re.sub(r'\[VISUAL CUE:[^\]]*\]', '', text)
    text = re.sub(r'\[MUSIC:[^\]]*\]', '', text)
    text = re.sub(r'\[TITLE CARD:[^\]]*\]', '', text)
    text = re.sub(r'\[B-ROLL:[^\]]*\]', '', text)
    text = re.sub(r'\[CUT TO:[^\]]*\]', '', text)

    # Clean up extra whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def split_on_pauses(text):
    """
    Split narration into segments separated by pause markers.
    Returns list of (type, content) tuples.
    type: 'speech' or 'pause'
    """
    segments = []
    pause_pattern = r'(\[PAUSE\]|\[LONG PAUSE\]|\[BEAT\])'
    parts = re.split(pause_pattern, text)

    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part in PAUSE_DURATIONS:
            segments.append(('pause', part))
        else:
            segments.append(('speech', part))

    return segments


def tts_chunk(text, voice_id):
    """
    Convert a single text chunk to audio bytes using edge-tts.
    Returns audio bytes or None on failure.
    """
    import subprocess
    import tempfile
    
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        temp_file = f.name
        
    cmd = ["edge-tts", "--text", text, "--voice", voice_id, "--write-media", temp_file]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        with open(temp_file, "rb") as f:
            audio_bytes = f.read()
        os.unlink(temp_file)
        return audio_bytes
    except subprocess.CalledProcessError as e:
        if os.path.exists(temp_file):
            os.unlink(temp_file)
        raise Exception(f"Edge TTS error: {e.stderr.decode()}")


def generate_silence(duration_secs, sample_rate=44100):
    """
    Generate silent MP3 audio bytes using FFmpeg.
    Used for [PAUSE] markers between TTS chunks.
    """
    import subprocess
    import tempfile
    
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        temp_file = f.name
        
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r={sample_rate}:cl=mono", 
        "-t", str(duration_secs), "-q:a", "2", "-acodec", "libmp3lame", temp_file
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        with open(temp_file, "rb") as f:
            silence_bytes = f.read()
        os.unlink(temp_file)
        return silence_bytes
    except Exception:
        if os.path.exists(temp_file):
            os.unlink(temp_file)
        return b''


def narrate_section(section, voice_id, output_dir, log_fn=print):
    """
    Convert one script section to audio using Edge TTS.
    Returns (audio_file_path, duration_secs) or (None, 0) on failure.
    """
    narration = section.get("narration", "")
    name      = section.get("name", "section").replace(" ", "_").lower()
    timestamp = section.get("timestamp", "0:00").replace(":", "_")

    clean   = clean_narration(narration)
    if not clean.strip():
        return None, 0

    segments = split_on_pauses(clean)
    audio_parts = []

    for seg_type, content in segments:
        if seg_type == 'pause':
            dur     = PAUSE_DURATIONS.get(content, 0.8)
            silence = generate_silence(dur)
            audio_parts.append(silence)
        else:
            if not content.strip():
                continue
            try:
                audio = tts_chunk(content, voice_id)
                audio_parts.append(audio)
                time.sleep(0.3)   # rate limit safety
            except Exception as e:
                log_fn(f"  ⚠ TTS chunk failed: {e}")
                continue

    if not audio_parts:
        return None, 0

    # Write to file — simple concatenation of MP3 chunks
    # (ElevenLabs returns MP3; we stitch them together)
    out_path = Path(output_dir) / f"{timestamp}_{name}.mp3"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, 'wb') as f:
        for part in audio_parts:
            f.write(part)

    # Estimate duration (rough: ~150 words per minute)
    word_count   = len(clean.split())
    pause_secs   = sum(PAUSE_DURATIONS.get(c, 0) for t, c in segments if t == 'pause')
    speech_secs  = (word_count / 150) * 60
    total_secs   = speech_secs + pause_secs

    return str(out_path), round(total_secs, 1)


def narrate_full_script(script, voice_id, output_dir, log_fn=print):
    """
    Narrate the complete script section by section.

    Returns:
    {
      "sections": [
        {"name": "HOOK", "audio_file": "/path/to/audio.mp3", "duration_secs": 45.2, "timestamp": "0:00", ...}
      ],
      "total_duration_secs": 920.5,
      "master_audio": "/path/to/master.mp3"  (all sections concatenated)
    }
    """
    if not voice_id:
        log_fn(f"  ⚠ No EDGE_TTS_VOICE — using default voice ({DEFAULT_VOICE})")
        voice_id = DEFAULT_VOICE

    sections      = script.get("sections", [])
    audio_dir     = Path(output_dir) / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    results     = []
    total_secs  = 0.0

    log_fn(f"  🎙  Narrating {len(sections)} sections...")

    for i, section in enumerate(sections):
        name = section.get("name", f"section_{i}")
        log_fn(f"  🎙  [{i+1}/{len(sections)}] {name}...", )

        audio_file, duration = narrate_section(
            section, voice_id, str(audio_dir), log_fn
        )

        if audio_file:
            results.append({
                "name":         section.get("name"),
                "timestamp":    section.get("timestamp", "0:00"),
                "audio_file":   audio_file,
                "duration_secs": duration,
                "broll_keywords": section.get("broll_keywords", []),
                "visual_treatment": section.get("visual_treatment", "slow_broll_narration"),
                "funny_moment": section.get("funny_moment"),
            })
            total_secs += duration
            log_fn(f" {duration:.0f}s")
        else:
            log_fn(f" failed")

    # Also narrate the CTA
    cta_text = script.get("cta_narration", "")
    if cta_text:
        log_fn("  🎙  CTA...")
        cta_section = {"name": "CTA", "narration": cta_text, "timestamp": "end"}
        cta_file, cta_dur = narrate_section(cta_section, voice_id, str(audio_dir), log_fn)
        if cta_file:
            results.append({
                "name": "CTA", "timestamp": "end",
                "audio_file": cta_file, "duration_secs": cta_dur,
                "broll_keywords": ["subscribe", "channel", "notification"],
                "visual_treatment": "clean_end_card",
                "funny_moment": None,
            })
            total_secs += cta_dur
            log_fn(f" {cta_dur:.0f}s")

    # Concatenate all sections into master audio using FFmpeg
    master_path = None
    if results:
        master_path = _concat_audio(
            [r["audio_file"] for r in results],
            str(Path(output_dir) / "master_narration.mp3"),
            log_fn
        )

    log_fn(f"  ✅ Narration complete — {total_secs/60:.1f} min total")

    return {
        "sections":            results,
        "total_duration_secs": round(total_secs, 1),
        "master_audio":        master_path,
    }


def _concat_audio(file_paths, output_path, log_fn=print):
    """Concatenate MP3 files using FFmpeg."""
    import subprocess
    import tempfile

    if not file_paths:
        return None
        
    work_dir = os.path.dirname(file_paths[0])

    # Create FFmpeg concat list
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', dir=work_dir, encoding='utf-8', delete=False) as f:
        for fp in file_paths:
            rel_name = os.path.basename(fp)
            f.write(f"file '{rel_name}'\n")
        list_file = f.name

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", os.path.basename(list_file),
        "-acodec", "libmp3lame",
        "-q:a", "2",
        os.path.abspath(output_path)
    ]

    try:
        result = subprocess.run(cmd, cwd=work_dir, capture_output=True, timeout=120)
        os.unlink(list_file)
        if result.returncode == 0:
            return output_path
        log_fn(f"  ⚠ Audio concat failed: {result.stderr.decode('utf-8', errors='ignore')}")
        return None
    except Exception as e:
        log_fn(f"  ⚠ Audio concat error: {e}")
        return None


def clone_voice_instructions():
    """Print setup instructions for using Edge TTS."""
    print("""
  🎙  VOICE SETUP
  ─────────────────────────────────────────────
  1. Edge TTS is completely free and requires no setup!
  2. You can preview voices natively.
  3. Default voice is set to: en-US-ChristopherNeural
  ─────────────────────────────────────────────
""")
