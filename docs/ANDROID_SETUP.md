# Android Shell APK Setup

This is the optional native Android app that hosts the Cyber AI
dashboard inside a locked-down WebView. It's separate from the Termux
connector (see `docs/TERMUX_SETUP.md`) — you can use one, the other,
or both.

## Getting the APK

You have three options:

### Option A — Download from GitHub Actions (recommended)

1. Push any change to `apps/android_shell/` (or trigger the workflow
   manually from the Actions tab).
2. In GitHub → Actions → "Android Shell APK" → the latest run →
   Artifacts: download `cyberai-android-shell-apks.zip`.
3. Unzip. You'll find:
   - `app-debug.apk` — installable immediately, useful for development.
   - `app-release-unsigned.apk` — needs signing before Android will
     install it (see "Signing the release APK" below).

### Option B — Build locally with Android Studio

1. Install [Android Studio](https://developer.android.com/studio)
   (Meerkat 2024.3+).
2. Open `apps/android_shell/` as an existing project. Studio will
   download the Gradle wrapper and Android SDK automatically.
3. Set your dashboard URL:
   - Edit `apps/android_shell/gradle.properties` and add:
     ```
     cyberaiDashboardUrl=https://cyberai.yourhost.com
     ```
4. `Build → Build App Bundle(s) / APK(s) → Build APK(s)`.
5. Look under `apps/android_shell/app/build/outputs/apk/debug/`.

### Option C — Build via command line

Requires JDK 17 and the Android SDK (with `ANDROID_HOME` set):

```bash
cd apps/android_shell
gradle wrapper --gradle-version 8.7
./gradlew assembleDebug \
  -PcyberaiDashboardUrl=https://cyberai.yourhost.com
```

APK will be at `app/build/outputs/apk/debug/app-debug.apk`.

## Installing on your phone

### Via USB (adb)

1. On the phone: Settings → About → tap "Build number" 7 times → go
   back to Settings → Developer options → enable "USB debugging".
2. Connect the phone.
3. On your computer:
   ```bash
   adb install app-debug.apk
   ```

### Via file transfer

1. Copy `app-debug.apk` to the phone (email, cloud drive, USB, etc.).
2. On the phone, tap the APK. If prompted, allow "Install unknown apps"
   for the file manager or browser you used.
3. Tap "Install".

## Signing the release APK

The debug APK is signed with Android's default debug key and installs
directly. For a release APK that could be distributed:

```bash
keytool -genkey -v -keystore ~/cyberai-release.keystore \
  -keyalg RSA -keysize 2048 -validity 10000 -alias cyberai

# Sign the unsigned release APK
apksigner sign --ks ~/cyberai-release.keystore \
  --out app-release-signed.apk \
  app-release-unsigned.apk

# Verify
apksigner verify app-release-signed.apk
```

Never commit the keystore to git. Keep the keystore password in a
password manager.

## What this app can and can't do

**Can:**
- Load the Cyber AI dashboard over HTTPS.
- Follow the same authentication flow the browser uses.
- Persist your session across app restarts (WebView cookies + local
  storage).

**Can't:**
- Access files, contacts, camera, microphone, or location — the
  manifest requests only `INTERNET` and `ACCESS_NETWORK_STATE`.
- Load anything over plain HTTP — cleartext traffic is disabled by the
  `network_security_config`.
- Open off-host URLs inside the WebView — links to other domains open
  in the system browser.

## Troubleshooting

**"App not installed" on install**
Usually caused by a previous install with a different signing key.
Uninstall the old copy first: Settings → Apps → Cyber AI → Uninstall.

**Blank screen after launch**
The build's `DASHBOARD_URL` is either wrong or the site is unreachable
from the phone. Check the URL in Android Studio's Logcat output, or
rebuild with the correct `cyberaiDashboardUrl` gradle property.

**"Your connection is not private"**
The dashboard's TLS certificate isn't trusted. For a public deployment,
get a real cert (Let's Encrypt). For internal testing over a private CA,
you'd need to add a `<trust-anchors>` entry with your CA in
`network_security_config.xml`.
