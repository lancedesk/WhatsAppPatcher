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

# Clean up previous builds
echo "[+] Cleaning up previous builds..."
rm -rf temp/

# Run the patcher with edit-manifest flag
echo "[+] Running patcher with manifest edit mode..."
echo "[!] The patcher will pause after extraction to allow edits"
echo ""

py main.py -p WhatsApp.apk -o PatchedWhatsApp.apk --edit-manifest

echo ""
echo "[+] =========================================="
echo "[+] Patching complete!"
echo "[+] Output: PatchedWhatsApp.apk"
echo "[+] =========================================="
    case $1 in
        --new-package)
            NEW_PACKAGE="$2"
            shift 2
            ;;
        --api-key)
            API_KEY="$2"
            shift 2
            ;;
        --output)
            OUTPUT_APK="$2"
            shift 2
            ;;
        --help)
            print_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            print_help
            exit 1
            ;;
    esac
done

echo -e "${GREEN}[+] WhatsApp Patcher - Automated Workflow${NC}"
echo ""

# Check dependencies
echo -e "${YELLOW}[*] Checking dependencies...${NC}"
command -v curl >/dev/null 2>&1 || { echo -e "${RED}[-] curl is required but not installed.${NC}"; exit 1; }
command -v python3 >/dev/null 2>&1 || command -v py >/dev/null 2>&1 || { echo -e "${RED}[-] Python 3 is required but not installed.${NC}"; exit 1; }
echo -e "${GREEN}[+] All dependencies found${NC}"
echo ""

# Create temp directory
mkdir -p "$TEMP_DIR"

# Download latest WhatsApp APK
echo -e "${YELLOW}[*] Downloading latest WhatsApp APK...${NC}"
echo -e "${YELLOW}[*] Fetching from APKMirror...${NC}"

# Get latest WhatsApp download link from APKMirror
# This is a simplified example - in production you'd parse the HTML page
APKMIRROR_URL="https://www.apkmirror.com/apk/whatsapp-inc/whatsapp/"

# Try to download with curl (note: APKMirror requires specific headers)
cd "$TEMP_DIR"

# Alternative: Use aria2c if available for faster downloads
if command -v aria2c >/dev/null 2>&1; then
    echo -e "${GREEN}[+] Using aria2c for faster download${NC}"
    # This would require finding the actual download URL first
else
    echo -e "${YELLOW}[*] Using curl for download${NC}"
fi

# Since direct APKMirror scraping is complex, we'll provide manual download option
echo ""
echo -e "${YELLOW}[!] Manual Download Required${NC}"
echo -e "${YELLOW}[!] Please download latest WhatsApp APK from:${NC}"
echo -e "${YELLOW}[!]   https://www.apkmirror.com/apk/whatsapp-inc/whatsapp/${NC}"
echo ""
echo -e "${YELLOW}[!] Save it in the current directory or provide path.${NC}"
read -p "Enter APK file path: " APK_INPUT

if [ ! -f "$APK_INPUT" ]; then
    echo -e "${RED}[-] File not found: $APK_INPUT${NC}"
    exit 1
fi

cd ..
LATEST_APK="$APK_INPUT"
echo -e "${GREEN}[+] APK found: $LATEST_APK${NC}"
echo ""

# Run the patcher
echo -e "${YELLOW}[*] Running patcher...${NC}"
echo -e "${YELLOW}[*] Package name: $NEW_PACKAGE${NC}"
echo -e "${YELLOW}[*] Output: $OUTPUT_APK${NC}"
echo ""

# Detect Python command
if command -v py >/dev/null 2>&1; then
    PYTHON_CMD="py -3"
else
    PYTHON_CMD="python3"
fi

# Build patcher command
PATCHER_CMD="$PYTHON_CMD main.py -p \"$LATEST_APK\" -o \"$OUTPUT_APK\""

if [ ! -z "$API_KEY" ]; then
    PATCHER_CMD="$PATCHER_CMD -g \"$API_KEY\""
fi

echo -e "${YELLOW}[*] Command: $PATCHER_CMD${NC}"
echo ""

# Run patcher
eval "$PATCHER_CMD"

PATCHER_EXIT_CODE=$?

if [ $PATCHER_EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}[+] Patching completed successfully!${NC}"
    echo -e "${GREEN}[+] Output APK: $OUTPUT_APK${NC}"
    echo ""
    echo -e "${GREEN}Installation Instructions:${NC}"
    echo -e "${GREEN}1. Transfer $OUTPUT_APK to your Android device${NC}"
    echo -e "${GREEN}2. Enable 'Unknown Sources' in Settings${NC}"
    echo -e "${GREEN}3. Install the APK${NC}"
    echo -e "${GREEN}4. Both official WhatsApp (com.whatsapp) and patched version ($NEW_PACKAGE) will run simultaneously${NC}"
    echo ""
else
    echo -e "${RED}[-] Patching failed with exit code $PATCHER_EXIT_CODE${NC}"
    exit 1
fi

# Cleanup
read -p "Clean up temporary files? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "$TEMP_DIR"
    echo -e "${GREEN}[+] Cleaned up temporary files${NC}"
fi
