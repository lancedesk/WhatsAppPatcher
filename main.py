import argparse
import os
import zipfile
import xml.etree.ElementTree as ET
import struct
import io
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


def change_package_name_in_apk(apk_path: Path, new_package: str) -> Path:
    """
    Modify the package name in AndroidManifest.xml by creating a modified copy.
    This must be done BEFORE patching to ensure signature validity.
    
    Args:
        apk_path: Path to the original APK file
        new_package: New package name (e.g., com.whatsapp.patched)
    
    Returns:
        Path to the modified APK (either original or modified copy)
    """
    if new_package == 'com.whatsapp':
        # Skip if trying to keep original package
        return apk_path
    
    print(f'[+] Creating input APK with package name: {new_package}...')
    
    try:
        # Read current manifest
        with zipfile.ZipFile(apk_path, 'r') as zip_ref:
            manifest_data = zip_ref.read('AndroidManifest.xml')
        
        # Binary string replacement in manifest
        original_bytes = b'com.whatsapp'
        new_bytes = new_package.encode('utf-8')
        
        # Count occurrences
        count = manifest_data.count(original_bytes)
        
        if count == 0:
            print(f'[!] Package name "com.whatsapp" not found in manifest - using original APK')
            return apk_path
        
        print(f'[*] Found {count} occurrence(s) of "com.whatsapp" in manifest')
        
        # Handle length differences
        if len(new_bytes) == len(original_bytes):
            # Same length - simple replacement
            modified_data = manifest_data.replace(original_bytes, new_bytes)
        elif len(new_bytes) < len(original_bytes):
            # Shorter - pad with nulls
            new_bytes_padded = new_bytes + b'\x00' * (len(original_bytes) - len(new_bytes))
            modified_data = manifest_data.replace(original_bytes, new_bytes_padded)
        else:
            # Longer - not safe, use original
            print(f'[!] New package name is longer than original - using original APK')
            return apk_path
        
        if modified_data != manifest_data:
            # Create modified APK copy in temp directory
            modified_apk = apk_path.parent / 'temp' / f"{apk_path.stem}_modified.apk"
            modified_apk.parent.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(apk_path, 'r') as zip_read:
                with zipfile.ZipFile(modified_apk, 'w', zipfile.ZIP_DEFLATED) as zip_write:
                    for item in zip_read.inlist():
                        data = zip_read.read(item.filename)
                        if item.filename == 'AndroidManifest.xml':
                            zip_write.writestr(item, modified_data)
                        else:
                            zip_write.writestr(item, data)
            
            print(f'[+] Modified APK created: {modified_apk}')
            return modified_apk
        else:
            print(f'[-] Failed to modify package name in binary data')
            return apk_path
            
    except Exception as e:
        print(f'[-] Failed to change package name: {e}')
        print('[-] Using original APK instead')
        import traceback
        traceback.print_exc()
        return apk_path


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
    
    # Create modified APK with new package name BEFORE patching (if requested)
    apk_to_patch = args.apk_path
    if args.new_package and args.new_package != 'com.whatsapp':
        apk_to_patch = change_package_name_in_apk(Path(args.apk_path), args.new_package)
    
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
            apk_path=str(apk_to_patch),  # Use modified APK if package name was changed
            output_apk=args.output,
            temp_path=args.temp_path,
            artifactory_list=artifactory_list,
            google_api_key=args.api_key,
            external_modules=external_modules,
            should_sign=args.should_sign,
            extra_artifacts=extra_artifacts,
    ) as stitch:
        stitch.patch()


if __name__ == '__main__':
    main()
