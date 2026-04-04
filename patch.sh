#!/bin/bash
# WhatsApp Patcher - Simple automated patch script

set -e

echo "[+] WhatsApp Patcher"
echo "[+] Starting patching process..."
echo ""

# Check if WhatsApp.apk exists
if [ ! -f "WhatsApp.apk" ]; then
    echo "[-] Error: WhatsApp.apk not found in current directory"
    echo "[!] Please ensure WhatsApp.apk is in the current directory"
    exit 1
fi

# Run the patcher with edit-manifest flag
# (main.py will handle temp directory cleanup)
echo "[+] Running patcher with manifest edit mode..."
echo "[!] The patcher will pause after extraction to allow edits"
echo "[!] You can run: py modify_manifest.py to change the package name"
echo ""

py main.py -p WhatsApp.apk -o PatchedWhatsApp.apk --edit-manifest

echo ""
echo "[+] =========================================="
echo "[+] Patching complete!"
echo "[+] Output: PatchedWhatsApp.apk"
echo "[+] Package name: com.whatsap2"
echo "[+] =========================================="
