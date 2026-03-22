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

        "ai": {
                    "name": "AI",
                    "description": "Pure AI content — models, tools, agents, and breakthroughs",
                    "cpm_range": "$18-40",
                    "channels": [
                                    "@aiexplained",
                                    "@matthewberman",
                                    "@mreflow",
                    ],
                    "trend_keywords": [
                                    "AI news 2026",
                                    "ChatGPT update",
                                    "OpenAI GPT-5",
                                    "Claude AI",
                                    "Gemini AI",
                                    "AI agent",
                                    "AI tool",
                                    "best AI 2026",
                                    "AI breakthrough",
                                    "AI vs human",
                    ],
        },

        "innovation": {
                    "name": "Innovation",
                    "description": "World-changing ideas, disruptive startups, and new inventions going viral",
                    "cpm_range": "$15-35",
                    "channels": [
                                    "@veritasium",
                                    "@coldFusion",
                                    "@realengineering",
                    ],
                    "trend_keywords": [
                                    "innovation 2026",
                                    "disruptive technology",
                                    "startup that changed the world",
                                    "new invention viral",
                                    "technology breakthrough 2026",
                                    "future technology",
                                    "next big thing tech",
                                    "world changing invention",
                                    "engineering marvel",
                                    "innovation story",
                    ],
        },

        "tech": {
                    "name": "Tech",
                    "description": "Consumer tech, gadgets, software, and the tech industry",
                    "cpm_range": "$12-30",
                    "channels": [
                                    "@mkbhd",
                                    "@linustechtips",
                                    "@unboxtherapy",
                    ],
                    "trend_keywords": [
                                    "best smartphone 2026",
                                    "new gadget review",
                                    "Apple vs Samsung",
                                    "tech news today",
                                    "new laptop 2026",
                                    "best tech 2026",
                                    "iPhone 17",
                                    "Samsung Galaxy S26",
                                    "tech deal",
                                    "unboxing viral",
                    ],
        },

        "invention": {
                    "name": "Invention",
                    "description": "New inventions, patents, and maker culture going viral on YouTube",
                    "cpm_range": "$14-32",
                    "channels": [
                                    "@hacksmith",
                                    "@stuffmadehere",
                                    "@markrober",
                    ],
                    "trend_keywords": [
                                    "new invention 2026",
                                    "crazy invention",
                                    "inventor builds",
                                    "homemade invention",
                                    "viral invention",
                                    "engineering invention",
                                    "DIY invention",
                                    "patent new technology",
                                    "inventor challenge",
                                    "impossible build",
                    ],
        },

        "hi_weapons": {
                    "name": "Hi-Tech Weapons & Defense",
                    "description": "Military tech, advanced weapons, defense innovation, and geopolitics",
                    "cpm_range": "$10-25",
                    "channels": [
                                    "@sandboxx",
                                    "@operatordrewski",
                                    "@thedrivermedia",
                    ],
                    "trend_keywords": [
                                    "new military technology",
                                    "advanced weapons 2026",
                                    "drone warfare",
                                    "hypersonic missile",
                                    "US military new weapon",
                                    "defense technology",
                                    "robot soldier",
                                    "laser weapon",
                                    "military drone AI",
                                    "next gen fighter jet",
                                    "autonomous weapon",
                                    "electronic warfare",
                    ],
        },

        "money": {
                    "name": "Money & Finance",
                    "description": "Personal finance, investing, wealth-building, and financial freedom",
                    "cpm_range": "$25-55",
                    "channels": [
                                    "@grahamstephan",
                                    "@andrei_jikh",
                                    "@minoritymindset",
                    ],
                    "trend_keywords": [
                                    "how to make money 2026",
                                    "passive income ideas",
                                    "invest money 2026",
                                    "stock market crash",
                                    "Bitcoin 2026",
                                    "crypto news today",
                                    "real estate investing",
                                    "side hustle",
                                    "financial freedom",
                                    "how to get rich",
                                    "millionaire habits",
                                    "recession proof income",
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
