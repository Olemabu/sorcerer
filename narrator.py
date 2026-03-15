"""
SORCERER — Narrator
====================
Converts script narration to audio using ElevenLabs.

Features:
  - Uses your cloned voice (set ELEVENLABS_VOICE_ID in .env)
  - Renders each script section separately for precise timing
  - Handles [PAUSE] markers by inserting silence
  - Strips visual cue markers before sending to TTS
  - Concatenates all sections into one master narration audio
  - Returns per-section audio files + timing data for compositor

Setup:
  1. Sign up at elevenlabs.io
  2. Go to Voices → Add Voice → Instant Clone
  3. Upload 3+ minutes of clean audio of yourself speaking
  4. Copy the Voice ID
  5. Add to .env: ELEVENLABS_VOICE_ID=your_voice_id_here
     ELEVENLABS_API_KEY=your_api_key_here

Recommended model: eleven_turbo_v2_5 (fastest, cheapest, excellent quality)
Cost: ~$0.05 per 15-minute video on Creator plan ($22/mo flat)
"""

import os
import re
import json
import time
import requests
from pathlib import Path

ELEVENLABS_API = "https://api.elevenlabs.io/v1"

# Best model for documentary narration — natural, authoritative
DEFAULT_MODEL   = "eleven_turbo_v2_5"
DEFAULT_VOICE   = "21m00Tcm4TlvDq8ikWAM"  # Rachel — fallback if no clone

# Voice settings tuned for documentary narration
VOICE_SETTINGS = {
    "stability":         0.55,   # 0-1. Higher = more consistent, less expressive
    "similarity_boost":  0.80,   # How closely to match the voice clone
    "style":             0.35,   # Expressiveness. 0.35 = authoritative but not robotic
    "use_speaker_boost": True,   # Enhances voice clarity
}

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


def tts_chunk(text, voice_id, api_key, model=DEFAULT_MODEL):
    """
    Convert a single text chunk to audio bytes.
    Returns audio bytes or None on failure.
    """
    r = requests.post(
        f"{ELEVENLABS_API}/text-to-speech/{voice_id}",
        headers={
            "xi-api-key":   api_key,
            "Content-Type": "application/json",
        },
        json={
            "text":           text,
            "model_id":       model,
            "voice_settings": VOICE_SETTINGS,
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.content


def generate_silence(duration_secs, sample_rate=44100):
    """
    Generate silent WAV audio bytes.
    Used for [PAUSE] markers between TTS chunks.
    """
    import struct
    import math

    num_samples  = int(sample_rate * duration_secs)
    num_channels = 1
    bits_per_sample = 16
    byte_rate    = sample_rate * num_channels * bits_per_sample // 8
    block_align  = num_channels * bits_per_sample // 8
    data_size    = num_samples * block_align

    header = struct.pack('<4sI4s4sIHHIIHH4sI',
        b'RIFF', 36 + data_size, b'WAVE',
        b'fmt ', 16, 1, num_channels,
        sample_rate, byte_rate, block_align,
        bits_per_sample, b'data', data_size
    )
    silence = b'\x00' * data_size
    return header + silence


def narrate_section(section, voice_id, api_key, output_dir, log_fn=print):
    """
    Convert one script section to audio.
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
                audio = tts_chunk(content, voice_id, api_key)
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


def narrate_full_script(script, voice_id, api_key, output_dir, log_fn=print):
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
    if not api_key:
        log_fn("  ⚠ No ELEVENLABS_API_KEY — skipping narration")
        return None

    if not voice_id:
        log_fn(f"  ⚠ No ELEVENLABS_VOICE_ID — using default voice ({DEFAULT_VOICE})")
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
            section, voice_id, api_key, str(audio_dir), log_fn
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
        cta_file, cta_dur = narrate_section(cta_section, voice_id, api_key, str(audio_dir), log_fn)
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

    # Create FFmpeg concat list
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for fp in file_paths:
            f.write(f"file '{fp}'\n")
        list_file = f.name

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-acodec", "libmp3lame",
        "-q:a", "2",
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        os.unlink(list_file)
        if result.returncode == 0:
            return output_path
        log_fn(f"  ⚠ Audio concat failed: {result.stderr[-200:]}")
        return None
    except Exception as e:
        log_fn(f"  ⚠ Audio concat error: {e}")
        return None


def clone_voice_instructions():
    """Print setup instructions for voice cloning."""
    print("""
  🎙  VOICE CLONE SETUP (one-time, 5 minutes)
  ─────────────────────────────────────────────
  1. Go to elevenlabs.io → Sign up (free tier works to start)
  2. Click Voices → Add Voice → Instant Voice Clone
  3. Name it (e.g. "My Voice")
  4. Upload audio: record yourself reading anything for 3+ minutes
     - Clear audio, no background noise
     - Normal speaking pace
     - Your natural narration voice
     - WAV or MP3, any quality
  5. Click Add Voice → copy the Voice ID
  6. Add to .env:
     ELEVENLABS_API_KEY=your_api_key
     ELEVENLABS_VOICE_ID=your_voice_id
  7. Done. Every video sounds like you.
  ─────────────────────────────────────────────
""")
