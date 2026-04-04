import argparse
import os
import sys
import shutil
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from stitch import Stitch
from stitch.common import ExternalModule
from stitch import patcher as stitch_patcher
from stitch import apk_utils

from artifactory_generator.firebase_params import FirebaseParamsFinder
from artifactory_generator.fmessage import FMessage
from artifactory_generator.dex_copier import DexCopier
from artifactory_generator.signature_finder import SignatureFinder
from artifactory_generator.decrypt_protobuf_finder import DecryptProtobufFinder


def modify_manifest_in_apk(apk_path: str, new_package: str) -> bool:
    """Modify package name in APK's binary manifest after compilation"""
    import tempfile
    
    print(f'[+] Modifying package name in compiled APK...')
    
    with open(apk_path, 'rb') as f:
        data = bytearray(f.read())
    
    old_package = 'com.whatsapp'
    
    # Try UTF-16-BE encoding (Android standard)
    patterns = [
        old_package.encode('utf-16-be') + b'\x00\x00',
    ]
    
    for pattern in patterns:
        if pattern in data:
            # Calculate proper padding
            old_bytes = pattern
            new_bytes = new_package.encode('utf-16-be') + b'\x00\x00'
            
            if len(new_bytes) > len(old_bytes):
                print(f'[-] New package too long')
                return False
            
            # Pad to match length
            if len(new_bytes) < len(old_bytes):
                new_bytes += b'\x00' * (len(old_bytes) - len(new_bytes))
            
            count = data.count(old_bytes)
            print(f'[+] Found {count} occurrence(s) of package name')
            data = data.replace(old_bytes, new_bytes)
            
            with open(apk_path, 'wb') as f:
                f.write(data)
            
            print(f'[✓] Package name changed to: {new_package}')
            return True
    
    print(f'[-] Could not find package pattern in APK')
    return False


def apply_windows_gradle_wrapper_fix() -> None:
    if os.name != 'nt':
        return

    original_check_call = stitch_patcher.subprocess.check_call

    def patched_check_call(command, *args, **kwargs):
        # Increase timeout for long-running operations like apktool
        if isinstance(command, list) and command:
            if 'apktool' in str(command):
                # Add -f flag to apktool d (decompile) to force overwrite existing directories
                if '-r' in command and '--output' in command:
                    # This is: apktool d -q -r --output <dir> <apk>
                    # Insert -f after -r
                    if '-f' not in command:
                        idx = command.index('-r')
                        command.insert(idx + 1, '-f')
                
                # Increase timeout from 1200s to 3600s (1 hour) for large APK builds
                kwargs['timeout'] = max(kwargs.get('timeout', 1200), 3600)
            elif command[0] == './gradlew':
                # On Windows, use shell=True so it finds gradlew.bat in cwd
                command_str = 'gradlew.bat ' + ' '.join(command[1:])
                return original_check_call(command_str, *args, shell=True, **kwargs)
        return original_check_call(command, *args, **kwargs)

    stitch_patcher.subprocess.check_call = patched_check_call


def force_cleanup_temp_dir(temp_path: str) -> None:
    """Force remove temp directory, handling Windows file locks"""
    import time
    
    temp = Path(temp_path)
    if not temp.exists():
        return
    
    # Try normal removal first
    try:
        shutil.rmtree(temp)
        return
    except (OSError, PermissionError):
        pass
    
    # If that fails, try Python's rmtree with ignore_errors
    try:
        shutil.rmtree(temp, ignore_errors=True)
        time.sleep(0.5)  # Small delay for file system to catch up
        if not temp.exists():
            return
    except:
        pass
    
    # Last resort: use system command
    if os.name == 'nt':
        try:
            os.system(f'rmdir /s /q "{temp}" 2>nul')
            time.sleep(0.5)
        except:
            pass


def increase_apktool_timeout() -> None:
    """Increase timeout for Apktool compilation on Windows (large APKs need more time)"""
    # The default timeout in Stitch's compile_apk is 1200 seconds (20 minutes)
    # For large APKs like WhatsApp (130+ MB), we need more time
    # We'll override the subprocess.run to use a much larger timeout
    
    import stitch.apk_utils as apk_utils
    original_check_call = apk_utils.subprocess.check_call
    
    def patched_check_call_timeout(command, *args, **kwargs):
        # If this is the apktool build command, increase timeout to 3600 seconds (60 minutes)
        if isinstance(command, list) and 'apktool' in str(command):
            kwargs['timeout'] = 3600  # 60 minutes
            print(f'[!] Increasing apktool timeout to 60 minutes for large APK...')
        return original_check_call(command, *args, **kwargs)
    
    apk_utils.subprocess.check_call = patched_check_call_timeout


def get_args():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-p', '--apk-path', dest='apk_path', help='APK path', required=True)
    parser.add_argument('-o', '--output', dest='output', help='Output APK path', required=False, default='output.apk')
    parser.add_argument('-t', '--temp', dest='temp_path', help='Temp path for extracted content', required=False,
                        default='./temp')
    parser.add_argument('-g', '--google-api-key', dest='api_key', help='Custom google api key', required=False,
                        default=None)
    parser.add_argument('--artifactory', dest='artifactory', help='Artifactory path', required=False,
                        default='./artifactory.json')
    parser.add_argument('--no-sign', dest='should_sign', help='Whether to sign the output APK', action='store_false',
                        required=False, default=True)
    parser.add_argument('--extra-artifacts', dest='extra_artifacts',
                        help='Extra artifact to add to the artifactory, in the format "key:value"',
                        required=False, default=[], nargs='+')
    parser.add_argument('--paywall', dest='paywall', help='Whether to add the paywall patch', required=False,
                        default=None)
    parser.add_argument('--edit-manifest', dest='edit_manifest', help='Pause after decompilation to edit AndroidManifest.xml', 
                        required=False, action='store_true', default=False)
    args, _ = parser.parse_known_args()
    return args


def main():
    apply_windows_gradle_wrapper_fix()
    increase_apktool_timeout()
    args = get_args()
    
    # Clean up previous temp directory (handling Windows file locks)
    force_cleanup_temp_dir(args.temp_path)
    
    extra_artifacts = {artifact.split(':')[0]: artifact.split(':')[1] for artifact in args.extra_artifacts}
    external_modules = [
        ExternalModule(Path(__file__).parent / './smali_generator',
                       'invoke-static {}, Lcom/smali_generator/TheAmazingPatch;->on_load()V')
    ]
    if args.paywall is not None:
        external_modules.append(ExternalModule(Path(args.paywall),
                                               'invoke-static {}, Lcom/paywall/Paywall;->on_load()V'))
    artifactory_list = [
        FMessage(args),
        DexCopier(args),
        SignatureFinder(args),
        DecryptProtobufFinder(args),
        FirebaseParamsFinder(args),
    ]
    
    # Convert temp_path to Path object
    temp_path = Path(args.temp_path)
    
    # Create Stitch instance
    with Stitch(
            apk_path=args.apk_path,
            output_apk=args.output,
            temp_path=temp_path,
            artifactory_list=artifactory_list,
            google_api_key=args.api_key,
            external_modules=external_modules,
            should_sign=args.should_sign,
            extra_artifacts=extra_artifacts,
    ) as stitch:
        # First, extract the APK
        print(f'[+] Extracting APK...')
        apk_utils.extract_apk(args.apk_path, temp_path)
        
        # If edit-manifest requested, pause before patching to let user edit
        if args.edit_manifest:
            # Check if we're in an interactive terminal
            if not sys.stdin.isatty():
                print(f'[-] Error: --edit-manifest requires an interactive terminal')
                print(f'[-] Please run without & (background) flag and ensure you have a terminal')
                return
            
            print(f'')
            print(f'[!] ==================== EDIT MANIFEST MODE ====================')
            print(f'[!] APK has been decompiled to: {temp_path}')
            print(f'')
            print(f'[!] You can now edit files:')
            print(f'[!]   • {temp_path}/apk/ - Decompiled smali and resources')
            print(f'[!]   • {temp_path}/apk/AndroidManifest.xml (binary XML - use hex editor or Apktool)')
            print(f'[!]   • {temp_path}/classes/ - Decompiled Java bytecode')
            print(f'')
            print(f'[!] Common edits:')
            print(f'[!]   - Change package: Edit AndroidManifest.xml package attribute')
            print(f'[!]   - Modify code: Edit .smali files')
            print(f'[!]   - Add resources: Add files to appropriate folders')
            print(f'')
            print(f'[!] Note: AndroidManifest.xml is in BINARY FORMAT.')
            print(f'[!] To edit it, either:')
            print(f'[!]   1. Use Apktool: apktool d <original>.apk, then get the decompiled version')
            print(f'[!]   2. Use a hex editor with knowledge of binary XML format')
            print(f'[!]   3. Use Frida/runtime hooks instead of modifying the APK')
            print(f'')
            print(f'[!] ============================================================')
            print(f'')
            
            try:
                input('[!] Press Enter when done editing files (and they are saved)...')
            except KeyboardInterrupt:
                print(f'')
                print(f'[-] Patch cancelled by user')
                return
        else:
            # If NOT in edit-manifest mode, clean extracted dir so patch() will re-extract
            extracted_path = Path(temp_path) / 'extracted'
            if extracted_path.exists():
                shutil.rmtree(extracted_path)
        
        # Continue with patching
        stitch.patch()
        
        # If edit-manifest was requested, modify the package name in the final APK
        if args.edit_manifest:
            print(f'')
            print(f'[+] Applying manifest modifications to final APK...')
            if modify_manifest_in_apk(args.output, 'com.whatsap2'):
                print(f'[✓] Manifest modified successfully!')
            else:
                print(f'[-] Warning: Could not modify manifest in final APK')
    
    print(f'')
    if args.edit_manifest:
        print(f'[+] Patching completed with edited manifest (com.whatsap2)!')
    else:
        print(f'[+] Patching completed!')


if __name__ == '__main__':
    main()
