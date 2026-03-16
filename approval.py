"""
VIDEO SORCERER — Telegram Approval Flow
=========================================
Review, revise, and approve video uploads
entirely from your Telegram app.

Flow:
  1. Video produced → preview sent to Telegram
  2. You review on your phone
  3. /approve → uploads to all platforms
  4. /revise [notes] → rebuilds with your changes
  5. Repeat until perfect

No computer needed. Everything from phone.
"""

import json
import os
import time
import threading
from pathlib import Path
from datetime import datetime


class ApprovalManager:
    def __init__(self, db_file, telegram_token, chat_id, log_fn=print):
        self.db_file  = Path(db_file)
        self.token    = telegram_token
        self.chat_id  = str(chat_id)
        self.log_fn   = log_fn
        self.queue    = self._load_queue()

    def _load_queue(self):
        queue_file = self.db_file.parent / "approval_queue.json"
        if queue_file.exists():
            try:
                return json.loads(queue_file.read_text())
            except Exception:
                pass
        return []

    def _save_queue(self):
        queue_file = self.db_file.parent / "approval_queue.json"
        queue_file.write_text(json.dumps(self.queue, indent=2))

    def _send(self, text, parse_mode="HTML"):
        import requests
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={
                    "chat_id":    self.chat_id,
                    "text":       text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True,
                },
                timeout=10,
            )
        except Exception as e:
            self.log_fn(f"  ⚠ Telegram send error: {e}")

    def queue_for_approval(self, video_path, script, direction,
                            board_actions, variation_brief,
                            captions=None, clips=None):
        """
        Add a produced video to the approval queue.
        Sends preview summary to Telegram.
        """
        video_id = f"video_{int(time.time())}"

        item = {
            "id":               video_id,
            "video_path":       str(video_path),
            "script_title":     script.get("title", "Untitled"),
            "style":            variation_brief.get("style", "hybrid"),
            "board":            variation_brief.get("board", "whiteboard"),
            "angle":            variation_brief.get("angle", "fear"),
            "created_at":       datetime.now().isoformat(),
            "status":           "pending",
            "revision_count":   0,
            "captions":         captions or {},
            "clips":            clips or {},
            "script":           script,
            "direction":        direction,
            "board_actions":    board_actions,
            "variation_brief":  variation_brief,
        }

        self.queue.append(item)
        self._save_queue()

        # Send preview to Telegram
        self._send_preview(item)
        return video_id

    def _send_preview(self, item):
        """Send video preview summary to Telegram for review."""
        script    = item.get("script", {})
        direction = item.get("direction", {})
        variation = item.get("variation_brief", {})

        viral    = direction.get("viral_moment", {})
        rep      = direction.get("replayability_score", {})
        safe     = direction.get("monetisation_safety", {})
        opening  = variation.get("opening", {})

        safety_emoji = {"green": "✅", "yellow": "⚠️", "red": "🚨"}.get(
            safe.get("overall_rating", "green"), "✅"
        )

        msg = (
            f"🎬 <b>VIDEO READY FOR REVIEW</b>\n"
            f"─────────────────────────\n\n"
            f"<b>{item['script_title']}</b>\n\n"
            f"🎨 Style: {item['style'].title()} on {item['board'].title()}\n"
            f"🎯 Angle: {item['angle'].title()}\n"
            f"🎬 Opens with: {opening.get('name','').replace('_',' ').title()}\n\n"
            f"🔴 Viral moment: {viral.get('timestamp','')} — "
            f"<i>\"{viral.get('narration_line','')[:80]}\"</i>\n\n"
            f"🔁 Replayability: {rep.get('score','?')}/10\n"
            f"{safety_emoji} Monetisation: {safe.get('overall_rating','').upper()}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>What would you like to do?</b>\n\n"
            f"✅ /approve — Upload to all platforms now\n"
            f"✏️ /revise [notes] — Tell me what to change\n"
            f"🎨 /restyle [style] — Change visual style\n"
            f"📋 /preview_script — See the full script\n"
            f"❌ /discard — Scrap this video\n\n"
            f"<i>Video ID: {item['id']}</i>"
        )
        self._send(msg)

    def get_pending(self):
        """Get the most recent pending video."""
        pending = [v for v in self.queue if v.get("status") == "pending"]
        return pending[-1] if pending else None

    def approve(self, video_id=None):
        """
        Approve a video for upload.
        Returns the video item ready for publishing.
        """
        if video_id:
            item = next((v for v in self.queue if v["id"] == video_id), None)
        else:
            item = self.get_pending()

        if not item:
            self._send("No video pending approval.")
            return None

        item["status"]      = "approved"
        item["approved_at"] = datetime.now().isoformat()
        self._save_queue()

        self._send(
            f"✅ <b>Approved!</b>\n\n"
            f"<b>{item['script_title']}</b>\n\n"
            f"Uploading to all enabled platforms now...\n"
            f"You'll get a confirmation when each platform is done."
        )

        return item

    def revise(self, notes, video_id=None):
        """
        Mark a video for revision with notes.
        Returns revision instructions.
        """
        if video_id:
            item = next((v for v in self.queue if v["id"] == video_id), None)
        else:
            item = self.get_pending()

        if not item:
            self._send("No video pending revision.")
            return None

        item["status"]         = "revising"
        item["revision_notes"] = notes
        item["revision_count"] = item.get("revision_count", 0) + 1
        self._save_queue()

        self._send(
            f"✏️ <b>Got it. Revising...</b>\n\n"
            f"Notes: <i>{notes}</i>\n\n"
            f"Revision #{item['revision_count']} — "
            f"I'll rebuild the affected sections and send you a new preview.\n\n"
            f"This takes 2-5 minutes."
        )

        return item

    def restyle(self, new_style, video_id=None):
        """Change the visual style and regenerate."""
        if video_id:
            item = next((v for v in self.queue if v["id"] == video_id), None)
        else:
            item = self.get_pending()

        if not item:
            self._send("No video to restyle.")
            return None

        old_style        = item.get("style", "hybrid")
        item["style"]    = new_style
        item["status"]   = "restyling"
        self._save_queue()

        self._send(
            f"🎨 <b>Restyling...</b>\n\n"
            f"From: {old_style.title()}\n"
            f"To: {new_style.title()}\n\n"
            f"Regenerating visual direction and board animations.\n"
            f"New preview coming in 2-3 minutes."
        )

        return item

    def discard(self, video_id=None):
        """Discard a video."""
        if video_id:
            item = next((v for v in self.queue if v["id"] == video_id), None)
        else:
            item = self.get_pending()

        if not item:
            self._send("No video to discard.")
            return

        item["status"] = "discarded"
        self._save_queue()

        self._send(
            f"❌ <b>Discarded.</b>\n\n"
            f"<i>{item['script_title']}</i> has been removed.\n\n"
            f"SORCERER will alert you when the next signal fires."
        )

    def confirm_upload(self, video_id, platform, url):
        """Confirm successful upload to a platform."""
        platform_emoji = {
            "youtube":   "▶️",
            "facebook":  "👥",
            "instagram": "📸",
            "tiktok":    "🎵",
            "twitter":   "𝕏",
            "telegram":  "✈️",
        }.get(platform, "✅")

        self._send(
            f"{platform_emoji} <b>{platform.title()} — UPLOADED</b>\n\n"
            f"<a href='{url}'>View your video →</a>"
        )

    def confirm_all_uploaded(self, video_id, results):
        """Send final confirmation when all platforms are done."""
        success = [p for p, r in results.items() if r.get("ok")]
        failed  = [p for p, r in results.items() if not r.get("ok")]

        msg = (
            f"🎉 <b>VIDEO IS LIVE!</b>\n\n"
            f"<b>{len(success)} platforms published</b>\n"
        )

        for platform in success:
            emoji = {"youtube":"▶️","facebook":"👥","instagram":"📸",
                     "tiktok":"🎵","twitter":"𝕏","telegram":"✈️"}.get(platform,"✅")
            msg += f"  {emoji} {platform.title()}\n"

        if failed:
            msg += f"\n⚠️ Failed: {', '.join(failed)}"

        msg += (
            f"\n\n🔥 <b>The Future Agent is live.</b>\n"
            f"SORCERER is watching for the next wave.\n"
            f"You'll be alerted the moment it hits."
        )

        self._send(msg)
