# Cyber AI Android Shell

A thin native Android WebView app that loads the Cyber AI dashboard
(the Next.js app deployed at your configured `CYBERAI_DASHBOARD_URL`)
inside a locked-down WebView. This is deliberately **not** where the
Termux connector logic lives — Termux is its own app, and this shell
just gives the operator a native-feeling entry point on Android.

Build via GitHub Actions (see `.github/workflows/android.yml`) or
locally with Android Studio (SDK 34, min SDK 26 = Android 8.0).

Why a WebView and not a fully native Compose app: keeps the mobile UI
byte-for-byte identical to the desktop dashboard and avoids duplicating
every feature in two codebases. The connector that actually reaches the
Termux shell is a separate Python app (`apps/termux_connector/`), so
this WebView shell has no elevated permissions and asks for no runtime
permissions at all.
