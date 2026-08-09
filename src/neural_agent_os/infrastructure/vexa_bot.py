"""Vexa-style Headless Web Meeting Bot for Google Meet, Teams, and Zoom.

Uses Playwright Chromium (headful) to join meetings as a named participant,
with concurrent FFmpeg system audio capture running in parallel.
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Optional

from neural_agent_os.infrastructure.logging import get_logger

logger = get_logger(__name__)


class VexaMeetingBot:
    """Headless Web Bot that joins online calls (Google Meet, Teams, Zoom) and records audio.
    
    Uses Playwright Chromium to appear as a named human participant.
    Concurrent FFmpeg loopback captures system audio for transcription.
    """

    BOT_DISPLAY_NAME = "Neural Agent Bot"

    PLATFORM_SELECTORS: dict[str, dict[str, str]] = {
        "google_meet": {
            "name_field": '[placeholder*="name" i], input[aria-label*="name" i]',
            "join_button": (
                'button[data-promo-anchor-id="join-button"], '
                'button:has-text("Ask to join"), '
                'button:has-text("Join now"), '
                'button:has-text("Join")'
            ),
        },
        "microsoft_teams": {
            "name_field": 'input[placeholder*="name" i], input[data-tid*="name" i]',
            "join_button": (
                'button:has-text("Join now"), '
                'button:has-text("Join meeting"), '
                'button:has-text("Join")'
            ),
        },
        "zoom": {
            "name_field": 'input[placeholder*="name" i], input#inputname, input[id*="name" i]',
            "join_button": (
                'button:has-text("Join"), '
                'button#joinBtn, '
                'a:has-text("Join from Your Browser")'
            ),
        },
    }

    def __init__(
        self,
        bot_name: str = "Neural Agent Bot",
        output_dir: Optional[str] = None,
    ) -> None:
        self.bot_name = bot_name
        self.output_dir = Path(output_dir) if output_dir else Path(os.path.expanduser("~/.transcribe/recordings"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.is_running = False
        self.current_proc: Optional[subprocess.Popen[bytes]] = None
        self.current_meeting_url: Optional[str] = None
        self.current_audio_path: Optional[Path] = None
        self._join_thread: Optional[threading.Thread] = None

    def detect_platform(self, url: str) -> str:
        """Identify call platform from URL."""
        url_lower = url.lower()
        if "meet.google.com" in url_lower:
            return "google_meet"
        elif "teams.microsoft.com" in url_lower or "teams.live.com" in url_lower:
            return "microsoft_teams"
        elif "zoom.us" in url_lower:
            return "zoom"
        else:
            return "generic_web"

    def _start_audio_capture(self, out_wav: Path) -> Optional[subprocess.Popen[bytes]]:
        """Start FFmpeg system audio loopback capture in background."""
        cmd = [
            "ffmpeg", "-y",
            "-f", "avfoundation",
            "-i", ":0",
            "-ar", "16000",
            "-ac", "1",
            str(out_wav),
        ]
        try:
            proc: subprocess.Popen[bytes] = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info(f"Audio capture started → {out_wav.name}")
            return proc
        except Exception as err:
            logger.warning(f"FFmpeg audio capture failed to start: {err}. Will use fallback.")
            # Write minimal valid WAV file as placeholder
            out_wav.write_bytes(
                b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
                b"\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
            )
            return None

    async def _join_playwright(self, url: str, duration_seconds: int, out_wav: Path) -> dict[str, Any]:
        """Use Playwright Chromium to join meeting as a named participant (async)."""
        try:
            from playwright.async_api import async_playwright  # type: ignore[import]
        except ImportError:
            logger.warning(
                "Playwright not installed. Install with: pip install playwright && playwright install chromium"
            )
            return {"status": "playwright_not_installed"}

        platform = self.detect_platform(url)
        selectors = self.PLATFORM_SELECTORS.get(platform, {})

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=False,
                    args=[
                        "--use-fake-ui-for-media-stream",
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-infobars",
                    ],
                )
                context = await browser.new_context(
                    permissions=["microphone", "camera"],
                )
                page = await context.new_page()

                logger.info(f"VexaMeetingBot navigating to {platform}: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                await page.wait_for_timeout(3_000)

                # Fill in display name
                if selectors.get("name_field"):
                    try:
                        await page.fill(selectors["name_field"], self.bot_name, timeout=5_000)
                        logger.info(f"Set bot display name: '{self.bot_name}'")
                    except Exception:
                        pass  # Name field not found or not needed

                # Click join button
                if selectors.get("join_button"):
                    try:
                        await page.click(selectors["join_button"], timeout=8_000)
                        logger.info("Clicked join button — bot is joining meeting")
                    except Exception:
                        logger.warning("Could not click join button automatically — may need manual joining")

                # Start parallel system audio capture
                audio_proc = self._start_audio_capture(out_wav)
                self.current_proc = audio_proc

                logger.info(f"Bot in meeting. Recording for up to {duration_seconds}s...")
                await page.wait_for_timeout(duration_seconds * 1_000)
                await browser.close()

                if audio_proc and audio_proc.poll() is None:
                    audio_proc.terminate()
                    try:
                        audio_proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        audio_proc.kill()

            return {
                "status": "completed",
                "platform": platform,
                "audio_path": str(out_wav),
                "duration_seconds": duration_seconds,
            }
        except Exception as err:
            logger.error(f"Playwright meeting bot error: {err}")
            return {"status": "error", "error": str(err), "platform": platform}

    def join_meeting(self, meeting_url: str, duration_seconds: int = 1800) -> dict[str, Any]:
        """Join a meeting URL as a bot participant and capture audio.
        
        Launches Playwright browser in a background thread so the API returns immediately.
        Audio recording starts simultaneously via FFmpeg loopback.
        """
        import asyncio

        platform = self.detect_platform(meeting_url)
        self.current_meeting_url = meeting_url
        self.is_running = True

        timestamp_str = time.strftime("%Y-%m-%d_%H-%M-%S")
        out_wav = self.output_dir / f"bot_{platform}_{timestamp_str}.wav"
        self.current_audio_path = out_wav

        def _run_async() -> None:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(
                    self._join_playwright(meeting_url, duration_seconds, out_wav)
                )
            finally:
                loop.close()
                self.is_running = False
                logger.info("Meeting bot session ended.")

        self._join_thread = threading.Thread(target=_run_async, daemon=True, name="vexa-bot")
        self._join_thread.start()

        logger.info(f"VexaMeetingBot launched for '{platform}': {meeting_url}")
        return {
            "status": "joined",
            "bot_name": self.bot_name,
            "platform": platform,
            "meeting_url": meeting_url,
            "audio_path": str(out_wav),
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "note": "Bot is joining in background. Call /api/connectors/bot/stop to stop and process.",
        }

    def stop_meeting(self) -> dict[str, Any]:
        """Leave meeting call, stop audio capture, and return path to captured audio."""
        if self.current_proc:
            try:
                self.current_proc.terminate()
                self.current_proc.wait(timeout=5)
            except Exception:
                try:
                    if self.current_proc:
                        self.current_proc.kill()
                except Exception:
                    pass

        audio_path = str(self.current_audio_path) if self.current_audio_path else None
        self.is_running = False
        self.current_proc = None

        return {
            "status": "stopped",
            "bot_name": self.bot_name,
            "audio_path": audio_path,
            "stopped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def get_status(self) -> dict[str, Any]:
        """Return current bot status."""
        return {
            "is_running": self.is_running,
            "meeting_url": self.current_meeting_url,
            "audio_path": str(self.current_audio_path) if self.current_audio_path else None,
            "bot_name": self.bot_name,
        }
