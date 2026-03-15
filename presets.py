"""
SORCERER — Presets
===================
Pre-loaded channels and keywords for specific niches.
Activated via /setup command in Telegram.

Curated for maximum signal quality and profit potential.
Each niche targets high-CPM advertisers.
"""

NICHES = {

    "ai_tech": {
        "name": "AI & Tech News",
        "description": "Breaking AI news, tools, and industry moves",
        "cpm_range": "$15-35",
        "channels": [
            "@aiexplained",
            "@matthewberman", 
            "@mreflow",
            "@bycloud",
            "@timdillonautomation",
            "@theprimagen",
            "@fireship",
            "@sentdex",
            "@yannic_kilcher",
            "@techwithtim",
        ],
        "trend_keywords": [
            "artificial intelligence news",
            "ChatGPT",
            "OpenAI",
            "AI agents 2026",
            "autonomous AI",
            "AI jobs",
            "machine learning breakthrough",
            "large language model",
            "AI startup",
            "generative AI",
        ],
    },

    "ai_healthcare": {
        "name": "AI in Healthcare",
        "description": "Medical AI, health tech, biotech breakthroughs",
        "cpm_range": "$25-60",
        "channels": [
            "@medicalfuturist",
            "@healthtechnerds",
            "@matthewberman",
            "@aiexplained",
            "@doctormike",
            "@healthcareai",
            "@biohackingcongress",
            "@singularityhub",
        ],
        "trend_keywords": [
            "AI healthcare",
            "medical AI diagnosis",
            "AI replace doctors",
            "healthcare automation",
            "AI cancer detection",
            "AI drug discovery",
            "robot surgery",
            "medical AI 2026",
            "AI longevity",
            "precision medicine AI",
            "AI mental health",
            "telemedicine AI",
        ],
    },

    "ai_innovation": {
        "name": "AI Innovation & Future",
        "description": "Emerging tech, future society, AI implications",
        "cpm_range": "$20-45",
        "channels": [
            "@kurzgesagt",
            "@veritasium",
            "@coldFusion",
            "@realengineering",
            "@twocentsworth",
            "@singularityhub",
            "@futurism",
            "@airevolution",
            "@wallstreetmillennial",
        ],
        "trend_keywords": [
            "future of AI",
            "AI replace jobs",
            "artificial general intelligence",
            "AGI timeline",
            "brain computer interface",
            "synthetic biology AI",
            "AI regulation",
            "AI ethics",
            "superintelligence",
            "technological singularity",
            "AI consciousness",
            "robot rights",
        ],
    },

    "full": {
        "name": "AI Tech + Healthcare + Innovation (Full Setup)",
        "description": "Everything — maximum coverage across all three niches",
        "cpm_range": "$20-60",
        "channels": [
            "@aiexplained",
            "@matthewberman",
            "@mreflow",
            "@bycloud",
            "@medicalfuturist",
            "@kurzgesagt",
            "@veritasium",
            "@coldFusion",
            "@timdillonautomation",
            "@singularityhub",
            "@fireship",
            "@healthtechnerds",
            "@realengineering",
            "@twocentsworth",
            "@wallstreetmillennial",
        ],
        "trend_keywords": [
            "artificial intelligence news",
            "ChatGPT",
            "OpenAI",
            "AI agents 2026",
            "autonomous AI",
            "AI jobs",
            "AI healthcare",
            "medical AI diagnosis",
            "AI replace doctors",
            "AI cancer detection",
            "AI drug discovery",
            "future of AI",
            "AGI timeline",
            "brain computer interface",
            "AI regulation",
            "AI longevity",
            "healthcare automation",
            "AI replace jobs",
            "robot surgery",
            "AI startup",
        ],
    },

}


def get_niche(niche_key):
    return NICHES.get(niche_key)


def list_niches():
    lines = []
    for key, niche in NICHES.items():
        lines.append(
            f"/{key}\n"
            f"  {niche['name']}\n"
            f"  {niche['description']}\n"
            f"  CPM: {niche['cpm_range']}\n"
            f"  {len(niche['channels'])} channels · {len(niche['trend_keywords'])} keywords"
        )
    return "\n\n".join(lines)
