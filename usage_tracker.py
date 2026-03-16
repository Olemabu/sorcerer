"""
SORCERER — Token Usage Tracker
================================
Tracks every Claude API call and reports cost.
Shows you exactly what each operation costs
before your bill arrives.

Displayed in every Telegram report so you
always know your running total.

Pricing (as of 2026):
  claude-opus-4-5:    $15 per 1M input tokens  / $75 per 1M output tokens
  claude-sonnet-4-6:  $3  per 1M input tokens  / $15 per 1M output tokens
  claude-haiku:       $0.25 per 1M input tokens / $1.25 per 1M output tokens
"""

import json
from datetime import datetime, date
from pathlib import Path


# ── Pricing per model (per 1M tokens) ─────────────────────────────────────────
PRICING = {
    "claude-opus-4-5": {
        "input":  15.00,
        "output": 75.00,
    },
    "claude-sonnet-4-6": {
        "input":  3.00,
        "output": 15.00,
    },
    "claude-haiku-4-5-20251001": {
        "input":  0.25,
        "output": 1.25,
    },
}

# ── Operation labels ───────────────────────────────────────────────────────────
OPERATION_LABELS = {
    "intelligence":    "💬 Comment analysis",
    "scriptwriter":    "✍️  Full script",
    "director":        "🎬 AI Director",
    "captions":        "📱 Platform captions",
    "board_actions":   "🖊️  Board direction",
    "clip_selection":  "✂️  Clip selection",
    "trends_keywords": "📈 Trend analysis",
}


class UsageTracker:
    def __init__(self, db_file):
        self.db_file      = Path(db_file)
        self.usage_file   = self.db_file.parent / "usage_log.json"
        self.session_cost = 0.0
        self.session_log  = []
        self._load()

    def _load(self):
        if self.usage_file.exists():
            try:
                self.data = json.loads(self.usage_file.read_text())
            except Exception:
                self.data = self._empty_data()
        else:
            self.data = self._empty_data()

    def _empty_data(self):
        return {
            "total_cost_usd":    0.0,
            "total_input_tokens":  0,
            "total_output_tokens": 0,
            "total_calls":         0,
            "daily":               {},
            "per_operation":       {},
            "last_reset":          datetime.now().isoformat(),
        }

    def _save(self):
        self.usage_file.write_text(json.dumps(self.data, indent=2))

    def calculate_cost(self, model, input_tokens, output_tokens):
        """Calculate cost in USD for a single API call."""
        pricing = PRICING.get(model, PRICING["claude-sonnet-4-6"])
        input_cost  = (input_tokens  / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)

    def record(self, operation, model, input_tokens, output_tokens, note=""):
        """Record a single API call."""
        cost = self.calculate_cost(model, input_tokens, output_tokens)

        # Session tracking
        self.session_cost += cost
        self.session_log.append({
            "operation":      operation,
            "model":          model,
            "input_tokens":   input_tokens,
            "output_tokens":  output_tokens,
            "cost_usd":       cost,
            "note":           note,
            "timestamp":      datetime.now().isoformat(),
        })

        # Persistent tracking
        today = date.today().isoformat()
        self.data["total_cost_usd"]      = round(self.data["total_cost_usd"] + cost, 6)
        self.data["total_input_tokens"]  += input_tokens
        self.data["total_output_tokens"] += output_tokens
        self.data["total_calls"]         += 1

        # Daily breakdown
        if today not in self.data["daily"]:
            self.data["daily"][today] = {"cost_usd": 0.0, "calls": 0}
        self.data["daily"][today]["cost_usd"] = round(
            self.data["daily"][today]["cost_usd"] + cost, 6)
        self.data["daily"][today]["calls"] += 1

        # Per operation breakdown
        if operation not in self.data["per_operation"]:
            self.data["per_operation"][operation] = {"cost_usd": 0.0, "calls": 0}
        self.data["per_operation"][operation]["cost_usd"] = round(
            self.data["per_operation"][operation]["cost_usd"] + cost, 6)
        self.data["per_operation"][operation]["calls"] += 1

        self._save()
        return cost

    def format_cost(self, cost_usd):
        """Format cost as readable string."""
        if cost_usd < 0.01:
            return f"${cost_usd:.4f}"
        return f"${cost_usd:.3f}"

    def session_summary(self):
        """Summary of costs for the current scan/production run."""
        if not self.session_log:
            return ""

        lines = ["💰 <b>TOKEN USAGE THIS RUN</b>\n"]
        for entry in self.session_log:
            label = OPERATION_LABELS.get(entry["operation"],
                                         entry["operation"])
            lines.append(
                f"{label}: {self.format_cost(entry['cost_usd'])} "
                f"({entry['input_tokens']:,}+{entry['output_tokens']:,} tokens)"
            )

        lines += [
            f"\n<b>This run: {self.format_cost(self.session_cost)}</b>",
            f"Today total: {self.format_cost(self.today_cost())}",
            f"All time: {self.format_cost(self.data['total_cost_usd'])}",
        ]

        # Budget warning
        today = self.today_cost()
        if today > 1.0:
            lines.append(f"\n⚠️ Today's spend is over $1.00")
        if self.data["total_cost_usd"] > 4.50:
            lines.append(f"\n🚨 Total spend approaching $5.00 — top up credits")

        return "\n".join(lines)

    def today_cost(self):
        today = date.today().isoformat()
        return self.data.get("daily", {}).get(today, {}).get("cost_usd", 0.0)

    def full_report_telegram(self):
        """Full usage report for /usage command."""
        d     = self.data
        today = date.today().isoformat()
        today_data = d.get("daily", {}).get(today, {})

        # Last 7 days
        days_block = ""
        for day, data in sorted(d.get("daily", {}).items())[-7:]:
            days_block += f"  {day}: {self.format_cost(data['cost_usd'])} ({data['calls']} calls)\n"

        # Per operation
        ops_block = ""
        for op, data in sorted(d.get("per_operation", {}).items(),
                                key=lambda x: x[1]["cost_usd"], reverse=True):
            label = OPERATION_LABELS.get(op, op)
            ops_block += f"  {label}: {self.format_cost(data['cost_usd'])} ({data['calls']} calls)\n"

        # Estimate remaining on $5
        remaining = max(0, 5.00 - d["total_cost_usd"])
        vids_remaining = int(remaining / 0.24) if remaining > 0 else 0

        return (
            f"💰 <b>SORCERER TOKEN USAGE</b>\n"
            f"─────────────────────────\n\n"
            f"<b>Today:</b> {self.format_cost(today_data.get('cost_usd', 0))} "
            f"({today_data.get('calls', 0)} calls)\n"
            f"<b>All time:</b> {self.format_cost(d['total_cost_usd'])}\n"
            f"<b>Total calls:</b> {d['total_calls']:,}\n"
            f"<b>Total tokens:</b> {(d['total_input_tokens'] + d['total_output_tokens']):,}\n\n"
            f"<b>Last 7 days:</b>\n{days_block}\n"
            f"<b>By operation:</b>\n{ops_block}\n"
            f"💵 <b>Remaining on $5:</b> {self.format_cost(remaining)}\n"
            f"📹 <b>Videos remaining:</b> ~{vids_remaining} at $0.24/video\n\n"
            f"<i>Top up at console.anthropic.com</i>"
        )

    def reset_session(self):
        """Reset session tracking for new scan."""
        self.session_cost = 0.0
        self.session_log  = []


# ── Patched Claude call that auto-tracks usage ─────────────────────────────────
def tracked_claude_call(operation, prompt, model, max_tokens,
                         anthropic_key, tracker=None, log_fn=print):
    """
    Drop-in replacement for raw requests.post to Anthropic.
    Automatically records token usage.
    Returns (response_text, cost_usd) or (None, 0) on failure.
    """
    import requests

    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":         anthropic_key,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json={
                "model":      model,
                "max_tokens": max_tokens,
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()

        text          = data["content"][0]["text"].strip()
        input_tokens  = data.get("usage", {}).get("input_tokens", 0)
        output_tokens = data.get("usage", {}).get("output_tokens", 0)

        cost = 0.0
        if tracker:
            cost = tracker.record(operation, model, input_tokens, output_tokens)
            log_fn(
                f"  💰 {OPERATION_LABELS.get(operation, operation)}: "
                f"${cost:.4f} ({input_tokens:,}+{output_tokens:,} tokens)"
            )

        return text, cost

    except Exception as e:
        log_fn(f"  ⚠ Claude call failed ({operation}): {e}")
        return None, 0.0
