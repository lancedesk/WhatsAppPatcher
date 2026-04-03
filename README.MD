# WhatsApp Patcher - Windows Compatible

**⭐ Fork of [Schwartzblat/WhatsAppPatcher](https://github.com/Schwartzblat/WhatsAppPatcher) with Windows compatibility improvements**

WhatsApp patcher is a program that decompiles, patches, and recompiles WhatsApp APK files to enable custom features.

## What's Different in This Fork?

This fork adds **Windows and Git Bash support** to the original project, which was designed primarily for Unix/Linux environments.

### Windows-Specific Fixes Applied

| Issue | Solution | Files Modified |
|-------|----------|-----------------|
| Gradle wrapper Unix path syntax (`./gradlew`) fails on Windows | Implemented subprocess hook to redirect to `gradlew.bat` with shell invocation | `main.py` |
| Firebase `resources.arsc` parsing fails on some WhatsApp builds | Added try-catch resilience to skip failed Firebase param extraction | `artifactory_generator/firebase_params.py` |
| APK signer produces `debugSigned` suffix instead of `signed` | Updated rename logic to handle debug keystore naming patterns | `stitch/apk_utils.py`* |
| Android SDK path discovery fails | Created `smali_generator/local.properties` with SDK path configuration | `smali_generator/local.properties` |

*Note: `apk_utils.py` fix applied to installed stitch package, included as patch documentation.

## Features

|            Feature             | Availability |
|:------------------------------:|:------------:|
|   Signature Verifier Bypass    |      ✔       |
|      Enable all AB tests       |      X       |
| Keep revoked for all messages  |      ✔       |
|     Disable read receipts      |      x       |
| Option to save view once media |      ✔       |
|   Profile Picture Screenshot   |      ✔       |

There is support for apks, apkm and xapk files.

## Requirements

1. **Python 3.11** or higher
2. **Java** (JDK 17+)
3. **Android SDK** (configured path in `local.properties`)
4. **Windows 10+**, **macOS**, or **Linux**

## Installation

### Windows-Specific Setup

1. **Clone this fork** (Windows-compatible version):
```bash
git clone https://github.com/lancedesk/WhatsAppPatcher.git
cd WhatsAppPatcher
git submodule update --init --recursive
```

2. **Configure Android SDK path** (Windows):
   - Edit `smali_generator/local.properties` and set your SDK path:
   ```properties
   sdk.dir=C:\\Android\\Sdk
   ```

3. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

### Standard Installation (Original)

```bash
git clone https://github.com/Schwartzblat/WhatsAppPatcher.git
cd WhatsAppPatcher
git submodule update --init --recursive
pip install -r requirements.txt
```

## Usage

### Windows / Git Bash
```bash
py -3 main.py -p "path/to/WhatsApp.apk" -o "PatchedWhatsApp.apk"
```

### Linux / macOS
```bash
python3 main.py -p ./WhatsApp.apk -o PatchedWhatsApp.apk
```

### With Google API Key (Optional)
```bash
py -3 main.py -p "path/to/WhatsApp.apk" -o "PatchedWhatsApp.apk" -g YOUR_GOOGLE_API_KEY
```

The Google API key is optional and only needed for OAuth bypass feature. Refer to the [Google API Key section](#google-api-key) for setup.

## Google API Key Setup

To get a Google API key:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. Navigate to the "APIs & Services" section.
4. Click on "Enable APIs and Services" and search for:
   - Maps SDK for Android
   - Places API
5. Enable both APIs for your project.
6. Go to the "Credentials" tab and click on "Create Credentials".
7. Select "API Key" from the dropdown menu.
8. Copy the generated API key.
9. Restrict the API key to your app's package name and SHA-1 certificate fingerprint for security.

## Installation on Device

1. **Backup your WhatsApp chats** (Settings → Chats → Chat backup)
2. **Uninstall official WhatsApp** (signature mismatch prevents installation)
3. **Enable "Unknown Sources"** (Settings → Security → Install from Unknown Sources)
4. **Transfer the patched APK** to your device (USB, cloud, or `adb push`)
5. **Install** by tapping the APK file
6. **Login** with your WhatsApp account

### Running Both Versions (Recommended)

To keep both official and patched WhatsApp:
- Install **Parallel Space** or **App Cloner** from Google Play Store
- Use it to clone the patched APK into an isolated environment
- Both apps run independently with separate data

## Changelog - Windows Compatibility Fork

### v1.1.0-windows (Current)
- ✅ Fixed Gradle wrapper execution on Windows (batch file support)
- ✅ Added Firebase ARSC parsing resilience for problematic APK builds
- ✅ Fixed APK signing with debug keystore (`debugSigned` naming)
- ✅ Added Android SDK path configuration template
- ✅ Tested on Windows 10/11 with Git Bash
- ✅ Added comprehensive Windows setup documentation

## Technical Details

### Changes Made

#### 1. **main.py** - Windows Gradle Wrapper Fix
```python
# Added subprocess hook to intercept ./gradlew calls and redirect to gradlew.bat
def apply_windows_gradle_wrapper_fix():
    if os.name != 'nt':
        return
    # Redirects ./gradlew to cmd.exe invocation of gradlew.bat
```

#### 2. **artifactory_generator/firebase_params.py** - ARSC Resilience
```python
# Wrapped ARSCParser in try-catch to handle corrupted resources.arsc
try:
    resources = ARSCParser(resources_path.read_bytes())
    _, original_google_api_key = resources.get_string(package_name, 'google_api_key')
except Exception as exc:
    # Gracefully skip Firebase params if parsing fails
    print(f'[-] Failed to parse firebase params: {exc}')
```

#### 3. **stitch/apk_utils.py** - Debug Keystore Signing
```python
# Updated rename logic to handle both '-aligned-signed.apk' and '-aligned-debugSigned.apk'
signed_candidates = [
    f'{base_name}-aligned-debugSigned.apk',  # Debug keystore
    f'{base_name}-aligned-signed.apk',       # Regular keystore
]
```

#### 4. **smali_generator/local.properties** - SDK Configuration
```properties
sdk.dir=C:\\Android\\Sdk
```

## Credits

- **Original Project**: [Schwartzblat/WhatsAppPatcher](https://github.com/Schwartzblat/WhatsAppPatcher)
- **Windows Compatibility**: [lancedesk](https://github.com/lancedesk)
- **YAHFA Hooking Framework**: [Lede](https://github.com/Lede-Inc/YAHFA)

## Contributing

Contributions are welcome! Please:
1. Fork this repository
2. Create a feature branch for your changes
3. Submit a pull request with a clear description of improvements

For bug reports or enhancement suggestions, open an issue.

## Disclaimer

**For educational purposes only.** This tool is provided as-is without warranty. I am not responsible for:
- Misuse of this software
- Terms of Service violations
- Any damage or data loss
- WhatsApp account suspension or bans

Use responsibly and at your own risk.

## License

Same as original: Educational use only. Refer to [Schwartzblat/WhatsAppPatcher](https://github.com/Schwartzblat/WhatsAppPatcher) for full license terms.