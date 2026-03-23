
# Resolution Mapping for Sorcerer

RESOLUTIONS = {
    "16:9":     {"width": 1920, "height": 1080, "name": "youtube"},
    "youtube":  {"width": 1920, "height": 1080, "name": "youtube"},
    "9:16":     {"width": 1080, "height": 1920, "name": "vertical"},
    "vertical": {"width": 1080, "height": 1920, "name": "vertical"},
    "tiktok":   {"width": 1080, "height": 1920, "name": "vertical"},
    "square":   {"width": 1080, "height": 1080, "name": "square"},
    "1:1":      {"width": 1080, "height": 1080, "name": "square"},
}

def get_resolution(ratio_str):
    """Return (width, height, name) for a given ratio string."""
    ratio_str = ratio_str.lower().strip()
    spec = RESOLUTIONS.get(ratio_str, RESOLUTIONS["16:9"])
    return spec["width"], spec["height"], spec["name"]
