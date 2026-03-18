"""
SORCERER — Visual Reference Repository (v3)
==============================================
6 clips deconstructed. Upload this + Project Bible at start of every session.
REF_004 "That's My King" = PRIMARY TARGET (clean voice-driven style)
REF_006 "Terence McKenna" = SECONDARY TARGET (layered palimpsest style)

BUILD ORDER at bottom — prioritized by impact and achievability.
"""

REF_001 = {
    "id": "ref_001_historical_opener",
    "source": "Effect For You — Old Historical Opener In After Effects",
    "style_tags": ["dark_cinematic", "historical", "grunge_texture", "documentary"],
    "mood": "somber, archival, weighty",
    "background": {"type": "dark grunge #1A1C1E", "texture": "heavy wear/patina", "vignette": "strong"},
    "typography": {"year": "massive serif cream", "subtitle": "gold caps #C49A3C", "body": "serif typewriter", "decorative": "faded italic atmosphere"},
    "images": {"style": "sepia B&W, brush-stroke alpha mask edges, Ken Burns parallax"},
    "transitions": {"type": "diagonal wipe with brush-stroke textured edge, ~0.8s"},
    "key_techniques": ["grunge textures", "brush-stroke photo masks", "serif typography", "diagonal wipe transitions", "element stagger timing"],
}

REF_002 = {
    "id": "ref_002_just_the_two_of_us",
    "source": "Just the Two of Us — Kinetic Typography Music Video",
    "style_tags": ["scrapbook", "warm_nostalgia", "world_builder", "music_video"],
    "mood": "romantic, warm, handcrafted",
    "background": {"type": "crumpled paper — light for verses, dark for chorus, golden for sun section", "key": "background CHANGES with mood"},
    "typography": {"style": "mixed rough/serif", "sizing": "key words 2-3x connecting words", "chorus": "white glow on dark"},
    "camera": {"type": "3D pan/zoom through scrapbook, parallax depth between layers"},
    "images": {"type": "physical props — camera, postcards, envelope, flower, photos"},
    "key_techniques": ["crumpled paper textures", "3D camera movement", "parallax layers", "mood-based bg switching", "prop compositing"],
}

REF_003 = {
    "id": "ref_003_maxxpace_commercial",
    "source": "MaxxPace Solutions — Kinetic Typography Promo",
    "style_tags": ["commercial", "fast_paced", "bold", "two_tone"],
    "mood": "energetic, confident, fast",
    "background": {"type": "clean flat — light grey then solid yellow #E8A820", "texture": "NONE"},
    "typography": {"font": "heavy bold sans", "hierarchy": "black primary, white secondary, yellow accent", "sizing": "massive variation"},
    "motion": {"speed": "4-6 frames per entrance", "motion_blur": "horizontal smear during deceleration", "word_stacking": "previous words REPOSITION", "rotation": "old text rotates 90° to edge"},
    "key_techniques": ["motion blur on entrance", "dynamic layout reflow", "text rotation", "shape mask reveals", "color wipe transitions", "0.5-0.75s per word pace"],
}

REF_004 = {
    "id": "ref_004_thats_my_king",
    "source": "That's My King — Dr. S.M. Lockridge (OFFICIAL)",
    "style_tags": ["spoken_word", "sermon", "grunge_parchment", "monochrome", "voice_driven"],
    "mood": "powerful, building, reverent",
    "PRIMARY_TARGET": True,

    "why_target": "Spoken word→kinetic type = exactly what SORCERER does. Monochrome. One texture. One image. Voice-driven sizing. Most powerful piece analysed. Achievable with 5 additions.",

    "background": {"color": (196, 184, 154), "type": "aged parchment, heavy grunge", "implementation": "ONE pre-rendered 1920x1080 PNG, reuse every frame"},
    "typography": {
        "font": "heavy condensed sans (Impact/Oswald/Bebas)",
        "colors": {"primary": (75, 65, 50), "emphasis": (55, 48, 38), "secondary": (120, 108, 85)},
        "sizing": {"key": "60-120px, 30-50% frame width", "emphasis": "40-60px", "connecting": "24-36px", "overflow": "120px+, bleeds off frame"},
        "layout": "left-aligned vertical stack, ragged right, right half of frame",
        "behavior": "REPLACE not accumulate",
        "sync": "word appears EXACTLY when spoken",
    },
    "image": {"type": "single persistent illustration, distressed, multiply blend, shifts position, 40-80% opacity"},
    "pacing": {"early": "3-4s per phrase", "middle": "2-3s", "climax": "1-2s rapid fire", "resolution": "held, centered"},

    "engine_needs": [
        "grunge parchment texture PNG (LOW effort, P1)",
        "per-word size variation (MEDIUM effort, P1)",
        "audio sync word timing via Edge-TTS (MEDIUM effort, P1)",
        "distressed image compositing with blend (LOW effort, P2)",
        "text-replace transitions (LOW effort, P2)",
    ],
}

REF_005 = {
    "id": "ref_005_mad_as_hell",
    "source": "I'm Mad As Hell — Network speech, by Aaron Leming",
    "style_tags": ["spoken_word", "camera_driven", "scattered_layout", "monochrome", "explosive"],
    "mood": "building rage, measured to explosive",

    "background": {"color": "warm beige/cream with subtle texture and vignette", "same_palette_as": "REF_004"},
    "typography": {
        "font": "bold sans-serif, dark brown/sepia, ONE font",
        "layout": "SPATIAL — words scattered by emotion, NOT in lines or grids",
        "rotation": "individual words/phrases at angles (90° vertical, circular explosion at climax)",
    },
    "camera": {
        "KEY_TECHNIQUE": "camera IS the animation — text is STATIC on oversized canvas, camera pans/zooms/rotates across it",
        "zoom_as_emphasis": "quiet = pulled back showing many words. LOUD = zoomed so tight one word fills frame",
        "motion_blur": "visible blur on fast camera whips between word clusters",
        "oversized_canvas": "words laid out on ~5000x3000, viewport (1920x1080) moves across it",
    },
    "pacing": {"measured_start": "slow pans", "building": "faster whips", "climax": "rapid zoom-ins, scattered explosive layout"},

    "key_techniques": [
        "oversized canvas + camera viewport (shared with REF_002)",
        "spatial word placement by emotion, not grammar",
        "word rotation at arbitrary angles",
        "zoom level = vocal intensity",
        "motion blur on camera whips",
        "text stays after appearing (accumulate mode)",
    ],
}

REF_006 = {
    "id": "ref_006_terence_mckenna",
    "source": "Is There Cause For Optimism? — Terence McKenna Kinetic Typography",
    "style_tags": ["spoken_word", "philosophical", "palimpsest", "dark_parchment", "layered"],
    "mood": "intellectual, deep, building layers of meaning",
    "SECONDARY_TARGET": True,

    "why_important": "Introduces PALIMPSEST technique — old text fades into background as new text arrives. Creates visual history of the argument. Perfect for documentary narration where ideas build on each other.",

    "background": {
        "color": "dark warm amber/burnt sienna #8B5E3C range",
        "type": "heavy grunge with visible canvas weave pattern, DARKER than REF_004",
        "letterbox": "black bars top and bottom",
    },
    "typography": {
        "font": "bold sans-serif with DISTRESSED/ROUGH edges — like woodblock press",
        "color": "very dark brown, nearly black against the amber background",
        "sizing": "varies by emphasis — same principle as REF_004",
        "PALIMPSEST_TECHNIQUE": {
            "description": (
                "OLD text doesn't disappear — it FADES to ~20% opacity and blends into "
                "the background texture over ~2 seconds. New text arrives bold and sharp. "
                "Result: 3-4 visible layers — current (100%), previous (40%), older (20%), "
                "oldest (barely visible, merged with texture). Creates visual DEPTH of argument."
            ),
            "implementation": (
                "Add 'fade_to' property on elements (target opacity instead of 0). "
                "Add 'persist' flag — element stays on screen at reduced opacity. "
                "Renderer keeps faded elements in a background composite layer."
            ),
        },
    },
    "particles": {
        "type": "ambient dark specks/embers floating slowly",
        "behavior": "low speed, no gravity, long life — atmospheric drift",
        "implementation": "our particle system exists, add 'ambient' mode",
    },
    "decorative": "small ornamental curls/flourishes below text — manuscript style",

    "key_techniques": [
        "PALIMPSEST — old text fades into texture, doesn't clear (KEY NEW TECHNIQUE)",
        "distressed text edges — rough/eroded, not clean antialiased",
        "dark warm parchment variant (vs cream in REF_004)",
        "ambient floating particles",
        "text stamped INTO surface, not sitting ON it",
        "decorative manuscript flourishes",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# UNIVERSAL PATTERNS (across all 6 clips)
# ═══════════════════════════════════════════════════════════════════════════════

UNIVERSAL = {
    "texture_always": "6/6 clips use textured backgrounds. ZERO flat colors. Texture is non-negotiable.",
    "per_word_sizing": "5/6 clips use dramatic size variation per word. THE #1 pro technique.",
    "audio_sync": "Every voice-driven clip syncs text to speech exactly. Non-negotiable for our use case.",
    "monochrome_power": "REF 004+005+006 (the 3 most powerful) all use single-color-family palettes. Restraint wins.",
    "camera_or_replace": "Text either REPLACES (004) or camera MOVES past it (005). Never static accumulation.",
    "palimpsest_depth": "REF 006 introduces fading old text into background — creates visual argument depth.",
    "oversized_canvas": "REF 002+005 both use camera viewport moving across larger canvas. Common technique.",
}


# ═══════════════════════════════════════════════════════════════════════════════
# UPDATED BUILD ORDER (revised with all 6 references)
# ═══════════════════════════════════════════════════════════════════════════════

BUILD_ORDER = [
    # --- PHASE 1: Unlock REF_004 target style ---
    "1. Grunge parchment texture PNGs — cream AND dark amber variants (unlocks REF 004+006)",
    "2. Per-word size variation — Sonnet outputs word-level size in scene JSON (unlocks ALL)",
    "3. Edge-TTS audio generation + word-level timestamp extraction (unlocks audio sync)",
    "4. Text-replace mode — phrases fade out, new phrases fade in (unlocks REF 004)",
    "5. Distressed image compositing — multiply blend, grunge mask (unlocks REF 004)",

    # --- PHASE 2: Unlock REF_006 palimpsest style ---
    "6. Palimpsest mode — old text fades to 20% opacity, persists as texture layer (unlocks REF 006)",
    "7. Distressed text edges — noise erosion mask on rendered text (unlocks REF 006)",
    "8. Ambient particle system — slow drift, no gravity, long life (unlocks REF 006)",

    # --- PHASE 3: Unlock remaining styles ---
    "9. Oversized canvas + camera viewport pan/zoom (unlocks REF 002+005)",
    "10. Motion blur on fast text/camera moves (unlocks REF 003+005)",
    "11. Spatial word placement — x,y per word, not sequential lines (unlocks REF 005)",
    "12. Word rotation at arbitrary angles (unlocks REF 005)",
    "13. Brush-stroke alpha masks for images (unlocks REF 001)",
    "14. Dynamic layout reflow — elements reposition when new ones arrive (unlocks REF 003)",
    "15. Crumpled paper textures + mood-based switching (unlocks REF 002)",
]


# ═══════════════════════════════════════════════════════════════════════════════
# TWO TARGET STYLES FOR SORCERER
# ═══════════════════════════════════════════════════════════════════════════════

STYLE_PROFILES = {
    "clean_power": {
        "description": "Like REF_004 'That's My King' — clean parchment, bold text, voice-driven sizing, replace mode",
        "use_when": "FEAR and HOPE acts — clear, direct, impactful statements",
        "background": "cream parchment",
        "text_behavior": "replace",
        "references": ["REF_004"],
    },
    "layered_depth": {
        "description": "Like REF_006 'McKenna' — dark parchment, palimpsest layering, ideas building on each other",
        "use_when": "MONEY and CONSEQUENCES acts — complex arguments, building cases, connecting dots",
        "background": "dark amber parchment",
        "text_behavior": "palimpsest",
        "references": ["REF_006"],
    },
}


# ═══════════════════════════════════════════════════════════════════════════════

REFERENCES = {
    "ref_001": REF_001, "ref_002": REF_002, "ref_003": REF_003,
    "ref_004": REF_004, "ref_005": REF_005, "ref_006": REF_006,
}

def get_target(): return REF_004
def get_secondary(): return REF_006

def list_all():
    for rid, ref in REFERENCES.items():
        tag = ""
        if ref.get("PRIMARY_TARGET"): tag = " ★ PRIMARY TARGET"
        elif ref.get("SECONDARY_TARGET"): tag = " ☆ SECONDARY TARGET"
        print(f"  {rid}: {ref['source']}{tag}")

def print_build_order():
    print("\n  BUILD ORDER:")
    for item in BUILD_ORDER: print(f"  {item}")

if __name__ == "__main__":
    list_all()
    print_build_order()
    print(f"\n  Styles: {list(STYLE_PROFILES.keys())}")
    print(f"  Universal patterns: {len(UNIVERSAL)}")
