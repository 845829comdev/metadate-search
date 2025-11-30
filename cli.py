#!/usr/bin/env python3
import argparse
import os
import json
from datetime import datetime

from core import UltraMetadataExtractor


def find_images(root, recursive=False):
    exts = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.webp', '.bmp', '.cr2', '.nef', '.arw', '.orf', '.rw2', '.dng'}
    if os.path.isfile(root):
        yield root
        return
    if not os.path.exists(root):
        return

    if recursive:
        for dirpath, dirs, files in os.walk(root):
            for f in files:
                if os.path.splitext(f)[1].lower() in exts:
                    yield os.path.join(dirpath, f)
    else:
        for f in os.listdir(root):
            full = os.path.join(root, f)
            if os.path.isfile(full) and os.path.splitext(f)[1].lower() in exts:
                yield full


def write_json(metadata, src_path, out_dir=None, suffix='_metadata'):
    base = os.path.basename(src_path)
    name = os.path.splitext(base)[0]
    out_name = f"{name}{suffix}.json"
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, out_name)
    else:
        out_path = os.path.join(os.path.dirname(src_path), out_name)

    payload = {
        'source_file': os.path.abspath(src_path),
        'extracted_at': datetime.now().isoformat(),
        'metadata': metadata
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return out_path


def main():
    parser = argparse.ArgumentParser(description='CLI extractor for MetaDate-JOOT')
    parser.add_argument('path', help='Image file or directory to process')
    parser.add_argument('--recursive', '-r', action='store_true', help='Recurse directories')
    parser.add_argument('--no-osint', action='store_true', help='Disable OSINT enhancements (network/geocoding)')
    parser.add_argument('--out', '-o', help='Output directory for JSON files')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of files processed (0 = no limit)')

    args = parser.parse_args()

    extractor = UltraMetadataExtractor()

    count = 0
    for img in find_images(args.path, recursive=args.recursive):
        if args.limit and count >= args.limit:
            break
        try:
            print(f"Processing: {img}")
            if args.no_osint:
                data = extractor.extract_metadata(img)
            else:
                data = extractor.extract_osint_metadata(img)

            out_path = write_json(data, img, out_dir=args.out)
            print(f"Saved metadata -> {out_path}\n")
            count += 1
        except Exception as e:
            print(f"Failed {img}: {e}")

    print(f"Done. Processed: {count}")


if __name__ == '__main__':
    main()
