#!/usr/bin/env python3
"""Persistent Read Aloud speak daemon — keeps edge-tts warm and streams audio ASAP."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

import edge_tts

CACHE = Path.home() / ".cache/read-aloud"
SOCK = CACHE / "speak.sock"
PID_FILE = CACHE / "daemon.pid"
LOG_FILE = Path("/tmp/speak-daemon.log")
DEFAULT_VOICE = os.environ.get("SPEAK_VOICE", "en-US-AndrewNeural")
MAX_CHARS = 50000


def log(msg: str) -> None:
    line = msg.rstrip() + "\n"
    try:
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError:
        pass


class SpeakDaemon:
    def __init__(self) -> None:
        self.generation = 0
        self.current_task: asyncio.Task | None = None
        self._procs: list[subprocess.Popen] = []

    async def stop(self) -> None:
        self.generation += 1
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            try:
                await self.current_task
            except (asyncio.CancelledError, Exception):
                pass
        self.current_task = None
        await asyncio.to_thread(self._kill_procs)

    def _kill_procs(self) -> None:
        for proc in list(self._procs):
            try:
                proc.terminate()
            except Exception:
                pass
        for proc in list(self._procs):
            try:
                proc.wait(timeout=0.4)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        self._procs.clear()

    def _ffmpeg(self) -> str | None:
        path = shutil.which("ffmpeg")
        if path:
            return path
        local = Path.home() / ".local/bin/ffmpeg"
        return str(local) if local.exists() else None

    def _play_stream_sync(
        self,
        text: str,
        voice: str,
        rate: str,
        volume: str,
        pitch: str,
        generation: int,
    ) -> None:
        if generation != self.generation:
            return

        ffmpeg = self._ffmpeg()
        if not ffmpeg or not shutil.which("paplay"):
            self._play_file_fallback_sync(text, voice, rate, volume, pitch, generation)
            return

        ff = subprocess.Popen(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                "pipe:0",
                "-f",
                "wav",
                "pipe:1",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        play = subprocess.Popen(
            ["paplay"],
            stdin=ff.stdout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if ff.stdout:
            ff.stdout.close()
        self._procs.extend([ff, play])

        try:
            # edge_tts stream is async — run a tiny event loop here.
            async def _pump() -> None:
                communicate = edge_tts.Communicate(
                    text, voice, rate=rate, volume=volume, pitch=pitch
                )
                assert ff.stdin is not None
                async for chunk in communicate.stream():
                    if generation != self.generation:
                        break
                    if chunk["type"] == "audio":
                        ff.stdin.write(chunk["data"])
                        ff.stdin.flush()
                ff.stdin.close()

            asyncio.run(_pump())
            play.wait(timeout=180)
        except Exception as exc:  # noqa: BLE001
            log(f"play_stream error: {exc}")
            self._play_file_fallback_sync(text, voice, rate, volume, pitch, generation)
        finally:
            for proc in (ff, play):
                try:
                    if proc.poll() is None:
                        proc.kill()
                except Exception:
                    pass
                if proc in self._procs:
                    self._procs.remove(proc)

    def _play_file_fallback_sync(
        self,
        text: str,
        voice: str,
        rate: str,
        volume: str,
        pitch: str,
        generation: int,
    ) -> None:
        if generation != self.generation:
            return
        mp3 = Path(tempfile.mktemp(prefix="speak-", suffix=".mp3"))
        try:
            async def _save() -> None:
                communicate = edge_tts.Communicate(
                    text, voice, rate=rate, volume=volume, pitch=pitch
                )
                await communicate.save(str(mp3))

            asyncio.run(_save())
            if generation != self.generation:
                return
            play = subprocess.Popen(
                ["paplay", str(mp3)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._procs.append(play)
            play.wait(timeout=180)
            if play in self._procs:
                self._procs.remove(play)
        except Exception as exc:  # noqa: BLE001
            log(f"fallback play error: {exc}")
        finally:
            mp3.unlink(missing_ok=True)

    async def _speak_job(self, msg: dict, generation: int) -> None:
        text = " ".join((msg.get("text") or "").split())[:MAX_CHARS]
        if not text:
            return
        voice = msg.get("voice") or DEFAULT_VOICE
        rate = msg.get("rate") or "+0%"
        volume = msg.get("volume") or "+0%"
        pitch = msg.get("pitch") or "+0Hz"
        log(f"speak start chars={len(text)} voice={voice} rate={rate}")
        # Stream the whole selection through one Edge connection and one player.
        # Splitting paragraphs into separate requests created multi-second pauses.
        await asyncio.to_thread(
            self._play_stream_sync, text, voice, rate, volume, pitch, generation
        )
        if generation != self.generation:
            log("speak cancelled")
            return
        log("speak done")

    async def handle_speak(self, msg: dict) -> None:
        await self.stop()
        generation = self.generation
        self.current_task = asyncio.create_task(self._speak_job(msg, generation))

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            raw = await reader.readline()
            if not raw:
                return
            msg = json.loads(raw.decode("utf-8"))
            action = msg.get("action") or "speak"
            if action == "stop":
                await self.stop()
                writer.write(b'{"ok":true,"stopped":true}\n')
            elif action == "ping":
                writer.write(b'{"ok":true,"pong":true}\n')
            elif action == "status":
                payload = {
                    "ok": True,
                    "generation": self.generation,
                    "busy": bool(self.current_task and not self.current_task.done()),
                    "ffmpeg": bool(self._ffmpeg()),
                    "paplay": bool(shutil.which("paplay")),
                }
                writer.write((json.dumps(payload) + "\n").encode("utf-8"))
            else:
                await self.handle_speak(msg)
                writer.write(b'{"ok":true,"queued":true}\n')
            await writer.drain()
        except Exception as exc:  # noqa: BLE001
            log(f"client error: {exc}")
            try:
                err = json.dumps({"ok": False, "error": str(exc)}) + "\n"
                writer.write(err.encode("utf-8"))
                await writer.drain()
            except Exception:
                pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass


async def run_server() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    if SOCK.exists():
        SOCK.unlink()
    PID_FILE.write_text(str(os.getpid()))
    log(f"daemon start pid={os.getpid()}")

    daemon = SpeakDaemon()
    server = await asyncio.start_unix_server(daemon.handle_client, path=str(SOCK))
    SOCK.chmod(0o600)

    def _shutdown(*_args) -> None:
        asyncio.create_task(daemon.stop())
        server.close()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _shutdown)
        except NotImplementedError:
            pass

    async with server:
        await server.serve_forever()


def main() -> None:
    local_bin = str(Path.home() / ".local/bin")
    os.environ["PATH"] = local_bin + os.pathsep + os.environ.get("PATH", "")
    try:
        asyncio.run(run_server())
    finally:
        SOCK.unlink(missing_ok=True)
        if PID_FILE.exists():
            try:
                if int(PID_FILE.read_text().strip()) == os.getpid():
                    PID_FILE.unlink(missing_ok=True)
            except ValueError:
                PID_FILE.unlink(missing_ok=True)
        log("daemon exit")


if __name__ == "__main__":
    main()
