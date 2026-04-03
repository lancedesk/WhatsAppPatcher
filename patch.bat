@echo off
REM WhatsApp Patcher - Automated Download & Patch Script (Windows)
REM Usage: patch.bat [OPTIONS]
REM Options:
REM   --new-package PACKAGE_NAME    Custom package name (default: com.whatsapp.patched)
REM   --api-key API_KEY              Google API key (optional)
REM   --output OUTPUT_PATH          Output APK path (default: PatchedWhatsApp.apk)
REM   --help                        Show this help message

setlocal enabledelayedexpansion

REM Default values
set "NEW_PACKAGE=com.whatsapp.patched"
set "API_KEY="
set "OUTPUT_APK=PatchedWhatsApp.apk"
set "TEMP_DIR=whatsapp_download"

REM Parse arguments
:parse_args
if "%1"=="" goto args_done
if "%1"=="--new-package" (
    set "NEW_PACKAGE=%2"
    shift
    shift
    goto parse_args
)
if "%1"=="--api-key" (
    set "API_KEY=%2"
    shift
    shift
    goto parse_args
)
if "%1"=="--output" (
    set "OUTPUT_APK=%2"
    shift
    shift
    goto parse_args
)
if "%1"=="--help" (
    goto print_help
)
shift
goto parse_args

:print_help
echo.
echo WhatsApp Patcher - Automated Download and Patch
echo.
echo Usage: patch.bat [OPTIONS]
echo.
echo Options:
echo     --new-package PACKAGE_NAME    Custom package name (default: com.whatsapp.patched)
echo     --api-key API_KEY             Google API key for OAuth bypass (optional)
echo     --output OUTPUT_PATH          Output APK path (default: PatchedWhatsApp.apk)
echo     --help                        Show this help message
echo.
echo Examples:
echo     patch.bat
echo     patch.bat --new-package com.whatsapp.modded
echo     patch.bat --api-key YOUR_KEY_HERE
echo.
pause
exit /b 0

:args_done
echo.
echo [+] WhatsApp Patcher - Automated Workflow
echo.

REM Check if Python is installed
py --version >nul 2>&1
if errorlevel 1 (
    echo [-] Python 3 is required but not found. Please install Python from python.org
    pause
    exit /b 1
)
echo [+] Python found

REM Create temp directory
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

REM Prompt for APK
echo.
echo [!] Manual Download Required
echo [!] Please download latest WhatsApp APK from:
echo [!]   https://www.apkmirror.com/apk/whatsapp-inc/whatsapp/
echo.
echo [!] Save it in the current directory or provide full path.
set /p APK_INPUT="Enter APK file path: "

if not exist "%APK_INPUT%" (
    echo [-] File not found: %APK_INPUT%
    pause
    exit /b 1
)

echo [+] APK found: %APK_INPUT%
echo.

REM Run the patcher
echo [*] Running patcher...
echo [*] Package name: %NEW_PACKAGE%
echo [*] Output: %OUTPUT_APK%
echo.

set "CMD=py -3 main.py -p "%APK_INPUT%" -o "%OUTPUT_APK%" --new-package "%NEW_PACKAGE%""

if not "%API_KEY%"=="" (
    set "CMD=!CMD! -g "%API_KEY%""
)

echo [*] Command: %CMD%
echo.

REM Execute patcher
call %CMD%

if errorlevel 1 (
    echo.
    echo [-] Patching failed!
    pause
    exit /b 1
)

echo.
echo [+] Patching completed successfully!
echo [+] Output APK: %OUTPUT_APK%
echo [+] Package name: %NEW_PACKAGE%
echo.
echo Installation Instructions:
echo 1. Transfer %OUTPUT_APK% to your Android device
echo 2. Enable 'Unknown Sources' in Settings
echo 3. Install the APK
echo 4. Both official WhatsApp (com.whatsapp) and patched version (%NEW_PACKAGE%) will run simultaneously
echo.

set /p cleanup="Clean up temporary files? (Y/N): "
if /i "%cleanup%"=="Y" (
    rmdir /s /q "%TEMP_DIR%"
    echo [+] Cleaned up temporary files
)

pause
