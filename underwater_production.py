
import os
import json
from dotenv import load_dotenv
from concept_lab import generate_series_bible
from pipeline import produce

load_dotenv()

def main():
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        print("❌ ANTHROPIC_API_KEY not found in .env")
        return

    # 1. Choose the "Underwater City" concept specifically
    concept = {
        "title": "Abyssal Metropolis: The Underwater City",
        "pitch": "A deep-dive into the engineering, biological, and economic reality of building cities under the sea. Not sci-fi, but near-future reality.",
        "niche": "Future Engineering / Science",
        "keywords": ["underwater city", "ocean colony", "blue economy", "marine engineering"]
    }

    print("🔍 Generating Series Bible and Pilot Script (Claude Opus)...")
    bible = generate_series_bible(concept, anthropic_key)
    
    if not bible or bible.get("_error"):
        print(f"❌ Bible generation failed: {bible.get('_error')}")
        return

    # Extract pilot script
    from concept_lab import extract_pilot_script
    script = extract_pilot_script(bible)
    
    print(f"✅ Script generated: {script.get('title')}")
    print(f"📍 Script length: {len(script.get('script_segments', []))} segments")

    # 2. Configure production
    config = {
        "anthropic_key": os.getenv("ANTHROPIC_API_KEY"),
        "edge_tts_voice": os.getenv("EDGE_TTS_VOICE", "en-US-ChristopherNeural"),
        "pexels_key": os.getenv("PEXELS_API_KEY"),
        "kling_key": os.getenv("KLING_API_KEY"),
        "freesound_key": os.getenv("FREESOUND_KEY"),
        "data_dir": os.getenv("SORCERER_DATA_DIR", "."),
        "publish_enabled": False, # Just produce for now
    }

    # Signal/Baseline for a "concept" video
    video = {
        "id": "concept",
        "title": script.get("title"),
        "channel_title": "Concept Lab",
    }
    signal = {"level": "CONCEPT", "multiplier": 0, "window": "manual"}
    baseline = {"median_vph": 100, "median_duration": 6}

    print("\n🚀 STARTING 12-STEP PRODUCTION PIPELINE (3D ENABLED)...")
    results = produce(
        video=video,
        signal=signal,
        baseline=baseline,
        comments=[],
        config=config,
        style_name="cinematic",
        log_fn=print,
        is_exact_text=True
    )

    if results.get("video_file"):
        print(f"\n🎉 PRODUCTION SUCCESS!")
        print(f"🎬 Video: {results['video_file']}")
        print(f"📄 Script: {results['script_file']}")
        print(f"📁 Output: {results['output_dir']}")
    else:
        print("\n❌ Production failed to produce a final video.")

if __name__ == "__main__":
    main()
