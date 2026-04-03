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


def apply_windows_gradle_wrapper_fix() -> None:
    if os.name != 'nt':
        return

    original_check_call = stitch_patcher.subprocess.check_call

    def patched_check_call(command, *args, **kwargs):
        if isinstance(command, list) and command and command[0] == './gradlew':
            # On Windows, use shell=True so it finds gradlew.bat in cwd
            command_str = 'gradlew.bat ' + ' '.join(command[1:])
            return original_check_call(command_str, *args, shell=True, **kwargs)
        return original_check_call(command, *args, **kwargs)

    stitch_patcher.subprocess.check_call = patched_check_call


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
    args = get_args()
    
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
        
        # Clean up extracted directory before calling patch()
        # (patch() will re-extract with proper structure for patching)
        extracted_path = Path(temp_path) / 'extracted'
        if extracted_path.exists():
            print(f'[+] Cleaning up for patching...')
            shutil.rmtree(extracted_path)
        
        # Continue with patching
        stitch.patch()
    
    print(f'')
    if args.edit_manifest:
        print(f'[+] Patching completed with edited manifest!')
    else:
        print(f'[+] Patching completed!')


if __name__ == '__main__':
    main()
