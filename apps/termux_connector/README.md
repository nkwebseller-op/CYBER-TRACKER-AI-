# Cyber AI Termux Connector

The Android-side companion for the Phase 9 Termux remote connector.

This is a small Python program that runs *inside Termux on your Android
device*, dials the Cyber AI backend's `/ws/termux` WebSocket, presents
the one-time pairing code you got out-of-band during registration, and
then executes reviewed diagnostic actions the backend forwards to it —
under the exact same PolicyEngine gate as any other Cyber AI action.

**What it never does:**
- It never accepts raw shell commands from the network — every message
  arrives as an already-vetted `argv` list built server-side from a
  reviewed command template (see
  `services/terminal/command_templates.py`).
- It never lets the backend read arbitrary files or your Android
  contacts — subprocess is invoked with a specific argv, working
  directory, and env override map, and that's it.
- It never runs an interactive shell.

See `docs/TERMUX_SETUP.md` for step-by-step Android install instructions.
