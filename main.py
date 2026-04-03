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
    Package name modification at build time is complex due to Android's binary XML format.
    
    Android stores the manifest as a binary XML file with a string pool. Modifying package names
    requires proper handling of offsets and length metadata, which is non-trivial.
    
    Instead of attempting binary modification, users have these options:
    1. Use Apktool: apktool d app.apk && modify && apktool b app
    2. Use Frida hooks to modify package name at runtime
    3. Install on Android and use Xposed/LSPosed modules
    4. This feature will work correctly in future versions when we integrate Apktool
    
    For now, this function returns the original APK unchanged.
    """
    if new_package == 'com.whatsapp':
        return apk_path
    
    print(f'[!] Package name modification requested: {new_package}')
    print(f'[!] This feature requires Apktool integration (coming in v1.3.0)')
    print(f'[!] Workaround: Use external tools after patching:')
    print(f'[!]   apktool d PatchedWhatsApp.apk')
    print(f'[!]   # Edit AndroidManifest.xml package attribute')
    print(f'[!]   apktool b PatchedWhatsApp')
    print(f'[!] Continuing with original package name for now...')
    
    return apk_path
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
    parser.add_argument('--new-package', dest='new_package', help='New package name (NOT YET IMPLEMENTED - requires Apktool integration)', 
                        required=False, default='com.whatsapp')
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
