#!/usr/bin/env python3
"""Modify package name in binary AndroidManifest.xml"""

def modify_manifest_package(manifest_path, new_package_name):
    """Modify package name in binary AndroidManifest.xml"""
    
    with open(manifest_path, 'rb') as f:
        data = bytearray(f.read())
    
    old_package = 'com.whatsapp'
    
    # Try different encodings
    patterns = [
        old_package.encode('utf-8') + b'\x00',       # UTF-8 with null
        old_package.encode('utf-16-be') + b'\x00\x00',  # UTF-16 with nulls
    ]
    
    found_pattern = None
    for i, pattern in enumerate(patterns):
        if pattern in data:
            found_pattern = (i, pattern)
            print(f'[+] Found package pattern (format {i}): {pattern[:40]}...')
            break
    
    if not found_pattern:
        print(f'[-] Package not found in any common format')
        return False
    
    encoding_id, old_bytes = found_pattern
    
    # Create replacement with same length
    new_bytes = new_package_name.encode('utf-8') + b'\x00'
    
    if len(new_bytes) > len(old_bytes):
        print(f'[-] ERROR: New package name too long')
        print(f'    Old: {len(old_bytes)} bytes')
        print(f'    New: {len(new_bytes)} bytes')
        return False
    
    # Pad to match length
    if len(new_bytes) < len(old_bytes):
        new_bytes += b'\x00' * (len(old_bytes) - len(new_bytes))
    
    print(f'[+] Replacing...')
    count = data.count(old_bytes)
    if count > 0:
        data = data.replace(old_bytes, new_bytes)
        
        with open(manifest_path, 'wb') as f:
            f.write(data)
        
        print(f'[✓] Modified {count} occurrence(s)!')
        print(f'[✓] New package: {new_package_name}')
        return True
    else:
        print(f'[-] Could not find pattern for replacement')
        return False

if __name__ == '__main__':
    import sys
    manifest = './temp/extracted/AndroidManifest.xml'
    new_pkg = sys.argv[1] if len(sys.argv) > 1 else 'com.whatsapp2'
    modify_manifest_package(manifest, new_pkg)
