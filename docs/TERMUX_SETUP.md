# Termux + Android Setup Guide

This guide walks you through connecting an **authorized** Android device
to your Cyber AI System via the Termux connector.

## What you'll need

- An Android phone or tablet (Android 8.0 / API 26 or newer).
- Your Cyber AI backend running somewhere reachable from the phone
  (e.g. `https://cyberai.yourhost.com`), with a valid TLS certificate.
- **Explicit written authorization** to test/monitor this specific
  device. Cyber AI is designed for authorized cybersecurity operations
  only.

## Step 1 — Install Termux on your Android device

Do **not** install Termux from the Google Play Store — that build has
been unmaintained for years and lacks the current package repos.

Instead, install from F-Droid or GitHub Releases:

- Open [https://f-droid.org/en/packages/com.termux/](https://f-droid.org/en/packages/com.termux/) on your phone.
- Tap "Download APK".
- Open the downloaded APK, allow installation from unknown sources when
  prompted, and complete the install.

Alternative: grab the latest Termux APK from the official releases page:
[https://github.com/termux/termux-app/releases](https://github.com/termux/termux-app/releases)

## Step 2 — Update Termux and install prerequisites

Open Termux. You'll see a prompt like `~ $`. Run:

```bash
pkg update -y && pkg upgrade -y
pkg install -y python git openssl
pip install --upgrade pip
pip install websockets
```

Wait for each command to finish. On a slow connection this can take
several minutes.

## Step 3 — Grab the connector script

```bash
mkdir -p ~/cyberai
cd ~/cyberai
curl -O https://raw.githubusercontent.com/nkwebseller-op/CYBER-TRACKER-AI-/claude/cyber-ai-foundation-upar86/apps/termux_connector/cyberai_termux.py
```

(Replace the URL with wherever you're hosting this repo — the above
points at the working branch.)

Sanity-check that it's the real script:

```bash
head -5 cyberai_termux.py
```

You should see the shebang plus the module docstring starting
`"""Cyber AI Termux Connector`.

## Step 4 — Register this device with your backend

From a browser or a machine that can talk to your backend (**not** from
the Termux command line — this call needs to be made by an authenticated
operator, not by the phone that's about to be paired):

```bash
curl -X POST https://cyberai.yourhost.com/api/termux/devices/register \
  -H 'Content-Type: application/json' \
  -d '{"name": "my-pixel-7"}'
```

The response looks like:

```json
{
  "device": {
    "id": "b3c1a9f4-...",
    "state": "PAIRING_REQUIRED",
    "platform": "ANDROID_TERMUX",
    ...
  },
  "pairingCode": "yF6Q1z",
  "expiresInSeconds": 300
}
```

**Write down the `device.id` (UUID) and the `pairingCode`.** The pairing
code is single-use and expires in five minutes.

## Step 5 — Confirm the pairing (still from the operator's machine)

Within five minutes:

```bash
DEVICE_ID="b3c1a9f4-..."      # from step 4
PAIRING_CODE="yF6Q1z"          # from step 4

curl -X POST https://cyberai.yourhost.com/api/termux/devices/$DEVICE_ID/pair \
  -H 'Content-Type: application/json' \
  -d "{\"pairingCode\": \"$PAIRING_CODE\"}"
```

The response contains the long-lived `deviceToken`:

```json
{
  "device": {"id": "b3c1a9f4-...", "state": "AUTHORIZED", ...},
  "deviceToken": "wV3H0Xq7...(long random string)"
}
```

**This is the only time the token is ever returned.** Copy it now — if
you lose it you'll have to revoke this device and re-register.

## Step 6 — Install the token on the phone (Termux side)

Back on the phone, in Termux:

```bash
mkdir -p ~/.cyberai
# Paste the token when prompted, then hit Ctrl-D:
cat > ~/.cyberai/device_token
# (paste the token here)
# Ctrl-D
chmod 600 ~/.cyberai/device_token
```

The `chmod 600` step is **mandatory** — the connector refuses to start
if the file is world-readable, because that would let any other Termux
app steal the token.

## Step 7 — Start the connector

Still in Termux:

```bash
cd ~/cyberai
python cyberai_termux.py \
  --url wss://cyberai.yourhost.com/ws/termux \
  --device-id b3c1a9f4-... \
  --token-file ~/.cyberai/device_token
```

You should see logs like:

```
[cyberai-termux] 2026-... connecting to wss://cyberai.yourhost.com/ws/termux
[cyberai-termux] 2026-... authenticated; awaiting command_request messages
```

Leave this running. When you open the Cyber AI dashboard and issue a
diagnostic against this device, the connector will execute it and stream
the result back.

## Step 8 — Keep the connector running in the background

Termux processes stop when the app is closed unless you either:

1. Use `termux-wake-lock` to prevent the OS from killing the process
   when the screen is off:

   ```bash
   pkg install termux-services
   termux-wake-lock
   python cyberai_termux.py --url ... --device-id ... --token-file ~/.cyberai/device_token
   ```

2. Or run it under `tmux` so it survives an app close:

   ```bash
   pkg install tmux
   tmux new -s cyberai
   # inside the tmux session:
   python cyberai_termux.py ...
   # detach with Ctrl-B then D
   ```

## Step 9 — Verify from the dashboard

Open the Cyber AI web dashboard, go to the Chat / Command Center, and
issue an authorized diagnostic. In the WebSocket panel you should see
`termux.device.connected`, then `termux.command.*` events as the
diagnostic runs.

## Revoking a device

If a device is lost, sold, or you just want to rotate the token:

```bash
curl -X POST https://cyberai.yourhost.com/api/termux/devices/$DEVICE_ID/revoke
```

The connector will lose its next connection attempt with
`authentication_failed`. Re-register from step 4 with a fresh code and
token.

## What the connector will and won't do

**Will:**
- Accept `command_request` messages from the paired backend and run the
  exact argv the backend built from a reviewed template
  (`services/terminal/command_templates.py`).
- Stream `stdout`/`stderr` back, honour timeouts, respect output caps.
- Reject any environment override whose key looks like a secret
  (`SECRET`, `TOKEN`, `PASSWORD`, `API_KEY`, ...).
- Reject any working directory outside `~`, `$PREFIX/tmp`, or `/tmp`.

**Won't:**
- Run raw shell strings. `argv[0]` containing `;`, `|`, `&`, `>`, `<`,
  `` ` ``, or `$` is refused immediately.
- Inherit the connector's own environment variables into the child
  process (the connector's token stays out of the child's env).
- Accept commands from anything other than the paired, authenticated
  WebSocket connection.

## Android APK shell (optional)

The `apps/android_shell/` project is a thin native Android WebView that
loads the Cyber AI dashboard so it feels like a real mobile app rather
than opening it in Chrome. It has nothing to do with Termux — Termux
still handles the actual connector work.

The GitHub Actions workflow `.github/workflows/android.yml` builds a
signed-with-debug-key APK on every push that touches `apps/android_shell/`.
Grab the artifact from the Actions run and install it via `adb install`
or by opening the `.apk` on the phone.

See `docs/ANDROID_SETUP.md` for step-by-step APK install instructions.
