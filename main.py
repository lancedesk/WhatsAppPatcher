import argparse
import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from stitch import Stitch
from stitch.common import ExternalModule
from stitch import patcher as stitch_patcher

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


def change_package_name(apk_path: Path, new_package: str) -> None:
    """
    Modify the package name in AndroidManifest.xml within the APK.
    
    Args:
        apk_path: Path to the APK file
        new_package: New package name (e.g., com.whatsapp.patched)
    """
    if new_package == 'com.whatsapp':
        # Skip if trying to keep original package
        return
    
    print(f'[+] Changing package name to {new_package}...')
    
    try:
        # Read APK as ZIP
        with zipfile.ZipFile(apk_path, 'r') as zip_ref:
            manifest_data = zip_ref.read('AndroidManifest.xml')
        
        # Register Android namespace
        ET.register_namespace('android', 'http://schemas.android.com/apk/res/android')
        
        # Parse manifest (binary XML, but we'll work with text approximation)
        # For binary XML in APK, we need a different approach
        # Use zipfile to modify directly
        with zipfile.ZipFile(apk_path, 'a') as zip_ref:
            # Extract, modify, and re-add manifest
            manifest_content = zip_ref.read('AndroidManifest.xml').decode('utf-8', errors='ignore')
            
            # Replace package name (simple string replacement for compatibility)
            modified_manifest = manifest_content.replace(
                'package="com.whatsapp"',
                f'package="{new_package}"'
            )
            
            if modified_manifest != manifest_content:
                # Remove old manifest and add modified one
                zip_ref.writestr('AndroidManifest.xml', modified_manifest)
                print(f'[+] Package name changed to {new_package}')
            else:
                print(f'[-] Could not change package name (manifest format unsupported)')
    except Exception as e:
        print(f'[-] Failed to change package name: {e}')
        print('[-] Continuing with original package name')


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
    parser.add_argument('--new-package', dest='new_package', help='New package name (default: com.whatsapp.patched)', 
                        required=False, default='com.whatsapp.patched')
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
    with Stitch(
            apk_path=args.apk_path,
            output_apk=args.output,
            temp_path=args.temp_path,
            artifactory_list=artifactory_list,
            google_api_key=args.api_key,
            external_modules=external_modules,
            should_sign=args.should_sign,
            extra_artifacts=extra_artifacts,
    ) as stitch:
        stitch.patch()
    
    # Change package name if specified
    if args.new_package and args.new_package != 'com.whatsapp':
        change_package_name(Path(args.output), args.new_package)


if __name__ == '__main__':
    main()
