"""
SORCERER — Alert System
Formats and delivers alerts.
Terminal output always.
Telegram if configured.
"""

import requests


# ── Terminal formatting ─────────────────────────────────────────────────────
def format_terminal(video, signal, baseline, intel):
    W   = 60
    bar = "█" * min(int(signal["multiplier"]), 25)

    lines = [
        "",
        f"  {signal['emoji']}  {signal['level']} SIGNAL DETECTED  —  {signal['window']} WINDOW",
        "═" * W,
        f"  Channel  : {video['channel_title']}",
        f"  Title    : {video['title'][:55]}{'…' if len(video['title']) > 55 else ''}",
        f"  Age      : {video['age_hours']}h old",
        f"  Views    : {video['views']:,}",
        f"  Rate     : {video['views_per_hour']:,.0f} views/hr",
        f"  Baseline : {baseline['median_vph']:,.0f} views/hr (their channel avg)",
        f"  Spike    : {signal['multiplier']}× above normal",
        f"  Momentum : {bar}",
        f"  URL      : https://youtube.com/watch?v={video['id']}",
        "─" * W,
    ]

    if not intel:
        lines += [
            "  (Intelligence layer disabled — add ANTHROPIC_API_KEY to .env)",
            "═" * W,
            "",
        ]
        return "\n".join(lines)

    if intel.get("_error"):
        lines += [f"  ⚠ Intelligence error: {intel['_error']}", "═" * W, ""]
        return "\n".join(lines)

    # Comment pulse
    lines += [
        "  💬  COMMENT PULSE",
        "  " + intel.get("comment_pulse", "—").replace(". ", ".\n  "),
        "─" * W,
    ]

    # Why spiking
    lines += [
        "  🔍  WHY IT'S SPIKING",
        "  " + intel.get("why_spiking", "—"),
        "─" * W,
    ]

    # Your move
    lines += [
        "  🎬  YOUR VIDEO",
        f"  Title  : {intel.get('my_video_angle', '—')}",
        f"  Hook   : {intel.get('hook_idea', '—')[:120]}",
        f"  Length : {intel.get('recommended_length_mins', '?')} min  —  {intel.get('length_reasoning', '')}",
        "",
        "  Structure:",
    ]
    for step in intel.get("content_structure", []):
        lines.append(f"    › {step}")

    lines.append("─" * W)

    # Paid push
    push = intel.get("worth_pushing_ads", False)
    lines += [
        "  💰  PAID PUSH",
        f"  Recommendation : {'PUSH IT ✓' if push else 'Skip ads'}",
        f"  Reason         : {intel.get('ad_reasoning', '—')}",
    ]
    if push:
        audience = ", ".join(intel.get("target_audience", []))
        lines += [
            f"  Audience       : {audience}",
            f"  Launch ads     : {intel.get('ad_timing', '—')}",
            f"  Budget         : {intel.get('estimated_budget', '—')}",
        ]

    lines += [
        "─" * W,
        f"  ⏰  {intel.get('urgency_note', '')}",
        "═" * W,
        "",
    ]

    return "\n".join(lines)


# ── Telegram formatting ─────────────────────────────────────────────────────
def format_telegram(video, signal, baseline, intel):
    url = f"https://youtube.com/watch?v={video['id']}"

    msg = (
        f"{signal['emoji']} <b>{signal['level']}</b> — {signal['window']} window\n\n"
        f"<b>{video['title']}</b>\n"
        f"📺 {video['channel_title']}\n"
        f"👁 {video['views']:,} views · {video['age_hours']}h old\n"
        f"⚡ <b>{signal['multiplier']}×</b> above their baseline\n"
        f"<a href='{url}'>Watch competitor video →</a>\n"
    )

    if not intel or intel.get("_error"):
        return msg

    push = intel.get("worth_pushing_ads", False)

    msg += (
        f"\n💬 <b>Comment pulse</b>\n{intel.get('comment_pulse', '—')}\n"
        f"\n🔍 <b>Why it's spiking</b>\n{intel.get('why_spiking', '—')}\n"
        f"\n🎬 <b>Make this video</b>\n"
        f"<b>{intel.get('my_video_angle', '—')}</b>\n"
        f"⏱ {intel.get('recommended_length_mins', '?')} min  —  {intel.get('length_reasoning', '')}\n"
        f"\n🎣 <b>Hook</b>\n{intel.get('hook_idea', '—')}\n"
    )

    structure = intel.get("content_structure", [])
    if structure:
        msg += "\n📋 <b>Structure</b>\n"
        for step in structure:
            msg += f"  › {step}\n"

    msg += f"\n💰 <b>Ads?</b> {'✅ PUSH IT' if push else '❌ Skip'}\n{intel.get('ad_reasoning', '')}\n"

    if push:
        audience = ", ".join(intel.get("target_audience", []))
        msg += (
            f"👥 {audience}\n"
            f"🕐 {intel.get('ad_timing', '—')}\n"
            f"💵 {intel.get('estimated_budget', '—')}\n"
        )

    msg += f"\n⏰ <i>{intel.get('urgency_note', '')}</i>"
    return msg


# ── Delivery ────────────────────────────────────────────────────────────────
def send_telegram(message, token, chat_id):
    if not token or not chat_id:
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id":                  chat_id,
                "text":                     message,
                "parse_mode":               "HTML",
                "disable_web_page_preview": False,
            },
            timeout=10,
        )
        return r.ok
    except Exception:
        return False


def deliver(video, signal, baseline, intel, telegram_token, telegram_chat_id, log_fn=print):
    """Format and deliver to all configured destinations."""
    terminal_msg  = format_terminal(video, signal, baseline, intel)
    log_fn(terminal_msg)

    telegram_msg = format_telegram(video, signal, baseline, intel)
    if send_telegram(telegram_msg, telegram_token, telegram_chat_id):
        log_fn("  → Telegram alert sent ✓")
    else:
        log_fn("  → Telegram not configured (terminal only)")
