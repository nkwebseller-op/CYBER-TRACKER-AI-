#!/usr/bin/env python3
"""Cyber AI Termux Connector — the Android side of Phase 9.

Runs inside Termux on the Android device. Speaks the `/ws/termux`
WebSocket protocol defined by `apps/api/app/ws/termux_gateway.py`:
authenticates once with a device token, then dispatches `command_request`
messages by running the exact argv the server sent and streaming stdout
/stderr / exit code back.

Requires only:
- python (Termux: `pkg install python`)
- websockets (Termux: `pip install websockets`)

Usage (after pairing — see docs/TERMUX_SETUP.md):

    python cyberai_termux.py \
        --url wss://your-cyberai-host/ws/termux \
        --device-id <uuid> \
        --token-file ~/.cyberai/device_token

The token is read from a mode-0600 file, never taken as a CLI arg (which
would show in `ps`) and never printed to logs.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    import websockets
    from websockets.exceptions import ConnectionClosed
except ImportError:
    print("ERROR: websockets is required. Install with: pip install websockets", file=sys.stderr)
    sys.exit(2)


# ---------------------------------------------------------------------------
# Safety configuration — hard ceilings the connector enforces on its own,
# independent of anything the server sends. If the server ever asks for
# more than these allow, the connector refuses (never obeys) and reports.
# ---------------------------------------------------------------------------

MAX_STDOUT_BYTES = 1_000_000  # 1 MB — matches backend default
MAX_STDERR_BYTES = 1_000_000
MAX_TIMEOUT_SECONDS = 120
MAX_ARGV_LENGTH = 64
MAX_ARG_LENGTH = 4096
# Working directory must live under one of these (real, resolved) prefixes.
DEFAULT_ALLOWED_ROOTS = [
    os.environ.get("HOME", "/data/data/com.termux/files/home"),
    "/data/data/com.termux/files/usr/tmp",
    "/tmp",
]


def _log(message: str) -> None:
    """Structured, single-line, secret-free logging. Never dumps the
    token, argv, or command output."""
    print(f"[cyberai-termux] {time.strftime('%Y-%m-%dT%H:%M:%S%z')} {message}", file=sys.stderr, flush=True)


class RefusedError(Exception):
    """The connector refused a server request on safety grounds. The
    protocol response is `command_failed` with an errorMessage — the
    connection stays open."""


# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------


def _validate_argv(argv: Any) -> list[str]:
    if not isinstance(argv, list) or not argv:
        raise RefusedError("argv must be a non-empty list")
    if len(argv) > MAX_ARGV_LENGTH:
        raise RefusedError(f"argv too long (limit {MAX_ARGV_LENGTH})")
    result: list[str] = []
    for part in argv:
        if not isinstance(part, str):
            raise RefusedError("argv element is not a string")
        if len(part) > MAX_ARG_LENGTH:
            raise RefusedError(f"argv element too long (limit {MAX_ARG_LENGTH})")
        if "\x00" in part:
            raise RefusedError("argv element contains NUL byte")
        result.append(part)
    # Blanket refusal of any shell metacharacter as an argv[0] — argv is
    # NEVER a shell string here.
    if any(c in result[0] for c in [";", "|", "&", ">", "<", "`", "$"]):
        raise RefusedError("argv[0] contains shell metacharacters")
    return result


def _validate_working_directory(path: Any) -> str | None:
    if path is None:
        return None
    if not isinstance(path, str):
        raise RefusedError("workingDirectory must be a string or null")
    resolved = os.path.realpath(path)
    if not any(resolved == root or resolved.startswith(root + os.sep) for root in DEFAULT_ALLOWED_ROOTS):
        raise RefusedError(f"workingDirectory {resolved!r} is outside allowed roots")
    if not os.path.isdir(resolved):
        raise RefusedError(f"workingDirectory {resolved!r} does not exist or is not a directory")
    return resolved


def _validate_env_overrides(env: Any) -> dict[str, str]:
    if env is None:
        return {}
    if not isinstance(env, dict):
        raise RefusedError("envOverrides must be a mapping or null")
    result: dict[str, str] = {}
    for key, value in env.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise RefusedError("envOverrides entries must be string key/value pairs")
        upper_key = key.upper()
        if any(
            bad in upper_key
            for bad in ("SECRET", "TOKEN", "PASSWORD", "PASSWD", "PRIVATE_KEY", "API_KEY", "APIKEY", "CREDENTIAL")
        ):
            raise RefusedError("refusing to accept secret-shaped env override")
        result[key] = value
    return result


def _validate_timeout(seconds: Any) -> float:
    if seconds is None:
        return 30.0
    if not isinstance(seconds, int | float) or seconds <= 0:
        raise RefusedError("timeoutSeconds must be a positive number")
    return min(float(seconds), float(MAX_TIMEOUT_SECONDS))


# ---------------------------------------------------------------------------
# Subprocess runner
# ---------------------------------------------------------------------------


async def _run_command(
    command_id: str,
    argv: list[str],
    working_dir: str | None,
    env_overrides: dict[str, str],
    timeout_seconds: float,
    send: callable,
) -> None:
    """Executes one already-vetted command. Streams stdout/stderr chunks
    to the server; sends a terminating command_completed / command_failed
    at the end. Always argv-based — never `shell=True`."""

    # Controlled child environment. Never inherits the connector's own
    # host env verbatim (which might contain the device token). Instead,
    # start from a minimal safe set + explicit overrides.
    base_env = {
        "PATH": os.environ.get("PATH", "/data/data/com.termux/files/usr/bin:/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/data/data/com.termux/files/home"),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "TERM": "dumb",
    }
    base_env.update(env_overrides)

    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=working_dir,
            env=base_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=hasattr(os, "setsid"),
        )
    except FileNotFoundError as exc:
        await send({
            "type": "command_failed",
            "commandId": command_id,
            "exitCode": None,
            "errorMessage": f"Executable not found: {exc}",
        })
        return
    except PermissionError as exc:
        await send({
            "type": "command_failed",
            "commandId": command_id,
            "exitCode": None,
            "errorMessage": f"Permission denied: {exc}",
        })
        return

    stdout_bytes = 0
    stderr_bytes = 0
    truncated_stdout = False
    truncated_stderr = False

    async def pump(stream: asyncio.StreamReader | None, kind: str) -> None:
        nonlocal stdout_bytes, stderr_bytes, truncated_stdout, truncated_stderr
        if stream is None:
            return
        while True:
            chunk = await stream.read(4096)
            if not chunk:
                return
            if kind == "stdout":
                cap = MAX_STDOUT_BYTES
                used = stdout_bytes
            else:
                cap = MAX_STDERR_BYTES
                used = stderr_bytes
            remaining = cap - used
            if remaining <= 0:
                if kind == "stdout":
                    truncated_stdout = True
                else:
                    truncated_stderr = True
                continue  # drain the pipe but drop
            if len(chunk) > remaining:
                chunk = chunk[:remaining]
                if kind == "stdout":
                    truncated_stdout = True
                else:
                    truncated_stderr = True
            text = chunk.decode(errors="replace")
            if kind == "stdout":
                stdout_bytes += len(chunk)
            else:
                stderr_bytes += len(chunk)
            await send({"type": kind, "commandId": command_id, "data": text})

    async def wait_and_pump() -> int | None:
        await asyncio.gather(pump(proc.stdout, "stdout"), pump(proc.stderr, "stderr"))
        return await proc.wait()

    try:
        exit_code = await asyncio.wait_for(wait_and_pump(), timeout=timeout_seconds)
    except TimeoutError:
        _terminate(proc)
        await send({
            "type": "command_failed",
            "commandId": command_id,
            "exitCode": None,
            "errorMessage": "timeout",
        })
        return
    except asyncio.CancelledError:
        _terminate(proc)
        raise

    if exit_code == 0:
        await send({"type": "command_completed", "commandId": command_id, "exitCode": 0})
    else:
        await send({
            "type": "command_failed",
            "commandId": command_id,
            "exitCode": exit_code,
            "errorMessage": f"exit_code={exit_code}",
        })


def _terminate(proc: asyncio.subprocess.Process) -> None:
    if proc.returncode is not None:
        return
    try:
        if hasattr(os, "killpg"):
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                return
            except (ProcessLookupError, PermissionError, OSError):
                pass
        proc.kill()
    except ProcessLookupError:
        pass


# ---------------------------------------------------------------------------
# WebSocket client
# ---------------------------------------------------------------------------


async def _connect_and_run(url: str, device_id: str, device_token: str, reconnect_delay: float) -> None:
    running_tasks: dict[str, asyncio.Task] = {}

    while True:
        try:
            _log(f"connecting to {url}")
            async with websockets.connect(url, ping_interval=30, ping_timeout=15) as ws:
                async def send(message: dict) -> None:
                    await ws.send(json.dumps(message))

                await send({"type": "auth", "deviceId": device_id, "deviceToken": device_token})
                first = json.loads(await ws.recv())
                if first.get("type") != "auth_ok":
                    _log(f"auth failed: {first.get('code')} — {first.get('message', '')}")
                    # Auth failure is fatal — no point retrying with the same wrong token.
                    return
                _log("authenticated; awaiting command_request messages")

                async for raw in ws:
                    try:
                        message = json.loads(raw)
                    except json.JSONDecodeError:
                        _log("malformed json from server — ignoring")
                        continue

                    msg_type = message.get("type")
                    command_id = message.get("commandId")

                    if msg_type == "command_request":
                        try:
                            argv = _validate_argv(message.get("argv"))
                            working_dir = _validate_working_directory(message.get("workingDirectory"))
                            env_overrides = _validate_env_overrides(message.get("envOverrides"))
                            timeout = _validate_timeout(message.get("timeoutSeconds"))
                        except RefusedError as exc:
                            _log(f"refused command: {exc}")
                            await send({
                                "type": "command_failed",
                                "commandId": command_id,
                                "exitCode": None,
                                "errorMessage": f"refused: {exc}",
                            })
                            continue
                        _log(f"executing command {command_id} argv0={argv[0]!r}")
                        task = asyncio.create_task(
                            _run_command(command_id, argv, working_dir, env_overrides, timeout, send)
                        )
                        running_tasks[command_id] = task

                        def _cleanup(t: asyncio.Task, cid=command_id) -> None:
                            running_tasks.pop(cid, None)

                        task.add_done_callback(_cleanup)

                    elif msg_type == "command_cancel":
                        task = running_tasks.pop(command_id, None)
                        if task and not task.done():
                            _log(f"cancelling {command_id}")
                            task.cancel()

                    else:
                        _log(f"unknown message type from server: {msg_type!r}")

        except ConnectionClosed as exc:
            _log(f"connection closed (code={exc.code}); retrying in {reconnect_delay}s")
        except (OSError, asyncio.TimeoutError) as exc:
            _log(f"connection error: {exc}; retrying in {reconnect_delay}s")

        for task in list(running_tasks.values()):
            task.cancel()
        running_tasks.clear()
        await asyncio.sleep(reconnect_delay)
        reconnect_delay = min(reconnect_delay * 2, 60.0)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _read_token_file(path: str) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        raise SystemExit(f"token file {p} does not exist")
    mode = p.stat().st_mode & 0o777
    if mode & 0o077:
        raise SystemExit(
            f"token file {p} has permissive mode {oct(mode)}; run: chmod 600 {shlex.quote(str(p))}"
        )
    token = p.read_text().strip()
    if not token:
        raise SystemExit(f"token file {p} is empty")
    return token


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Cyber AI Termux Connector")
    parser.add_argument("--url", required=True, help="wss://.../ws/termux endpoint")
    parser.add_argument("--device-id", required=True, help="UUID from device registration")
    parser.add_argument(
        "--token-file",
        default="~/.cyberai/device_token",
        help="Path to a mode-0600 file containing the device token",
    )
    parser.add_argument("--reconnect-delay", type=float, default=2.0)
    args = parser.parse_args(argv)

    token = _read_token_file(args.token_file)

    try:
        asyncio.run(
            _connect_and_run(
                url=args.url,
                device_id=args.device_id,
                device_token=token,
                reconnect_delay=args.reconnect_delay,
            )
        )
    except KeyboardInterrupt:
        _log("interrupted; exiting")


if __name__ == "__main__":
    main()
