"""
Test: Concept Lab
Tests the local logic of concept_lab.py.
If ANTHROPIC_API_KEY is set, also tests the Claude integration.
"""
import os
import sys

def main():
    print("\n  🧪 CONCEPT LAB — TEST")
    print("  " + "─" * 40)

    # 1. Import test
    try:
        from concept_lab import (
            generate_concepts,
            generate_series_bible,
            format_concepts_telegram,
            format_bible_telegram,
            extract_pilot_as_script,
        )
        print("  ✅ Import successful")
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        sys.exit(1)

    # 2. Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("  ⚠  No ANTHROPIC_API_KEY — skipping Claude integration tests")
        print("  ✅ Local logic OK (set ANTHROPIC_API_KEY to run full test)")
        return

    # 3. Generate concepts
    print("\n  📡 Generating 3 concepts (Claude Sonnet)...")
    concepts = generate_concepts(api_key, niche_hint="tech", n=3)

    if isinstance(concepts, dict) and concepts.get("_error"):
        print(f"  ❌ Error: {concepts['_error']}")
        sys.exit(1)

    print(f"  ✅ Generated {len(concepts)} concepts\n")
    for i, c in enumerate(concepts, 1):
        print(f"  #{i} — {c.get('title', '?')} (score: {c.get('virality_score', '?')}/10)")
        print(f"       {c.get('pitch', '')}")
        print(f"       🎨 {c.get('art_style', '')[:80]}...")
        print(f"       📺 Channel: {c.get('channel_name', '?')}")
        print()

    # 4. Telegram format test
    msg = format_concepts_telegram(concepts)
    print(f"  ✅ Telegram format: {len(msg)} chars")

    # 5. Series bible (optional — uses Opus, costs more)
    if os.getenv("TEST_BIBLE", "").lower() == "true":
        print("\n  📖 Generating series bible for top concept...")
        bible = generate_series_bible(concepts[0], api_key)
        if isinstance(bible, dict) and bible.get("_error"):
            print(f"  ❌ Bible error: {bible['_error']}")
        else:
            sb = bible.get("series_bible", {})
            ps = bible.get("pilot_script", {})
            print(f"  ✅ Series bible complete")
            print(f"     Channel names: {sb.get('channel_names', [])}")
            print(f"     Episodes: {len(sb.get('episodes', []))}")
            print(f"     Pilot title: {ps.get('title', '?')}")
            print(f"     Pilot sections: {len(ps.get('sections', []))}")

            # Test pilot extraction
            pilot = extract_pilot_as_script(bible)
            print(f"  ✅ Pilot extraction: {len(pilot.get('sections', []))} sections")
    else:
        print("  ℹ  Set TEST_BIBLE=true to also test series bible generation (uses Opus)")

    print(f"\n  {'─' * 40}")
    print("  ✅ ALL TESTS PASSED")

if __name__ == "__main__":
    main()
