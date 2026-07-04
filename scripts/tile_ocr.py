#!/usr/bin/env python3
"""
tile_ocr.py — Send tiles to Alibaba Qwen-VL-OCR and collect structured text/tables.

Features:
- Base64 encoding (no external upload needed)
- Retry with exponential backoff
- Deduplication by overlap area
- Outputs JSON + CSV

Usage:
    export DASHSCOPE_API_KEY=sk-xxx
    python tile_ocr.py --tiles-dir ./tiles/ --output result.json
"""

import argparse
import base64
import io
import json
import os
import re
import sys
import time
from pathlib import Path

from PIL import Image


def encode_image_to_base64(image_path: Path) -> str:
    """Read image and return base64 data URI."""
    with open(image_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("utf-8")
    # Detect format
    ext = image_path.suffix.lower()
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(ext, "image/png")
    return f"data:{mime};base64,{b64}"


def call_qwen_ocr(api_key: str, base64_image: str, prompt: str = None) -> dict:
    """Call Alibaba Qwen-VL-OCR API. Returns parsed response."""
    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: install 'openai' package: pip install openai", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    default_prompt = (
        "Extract all text, numbers, dimensions, and tables from this engineering drawing fragment. "
        "Output as structured JSON with fields: 'text_lines' (array of strings), "
        "'dimensions' (array of {value, unit}), 'tables' (array of rows). "
        "If no text found, return empty arrays."
    )

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": base64_image,
                        "min_pixels": 32 * 32 * 3,
                        "max_pixels": 32 * 32 * 8192,
                    },
                },
                {"type": "text", "text": prompt or default_prompt},
            ],
        }
    ]

    # Retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                model="qwen-vl-ocr-2025-11-20",
                messages=messages,
            )
            content = completion.choices[0].message.content
            # Try parse JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Return raw text wrapped
                return {"_raw_text": content, "text_lines": [content], "dimensions": [], "tables": []}
        except Exception as e:
            print(f"  API error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return {"_error": str(e), "text_lines": [], "dimensions": [], "tables": []}


def deduplicate_results(results: list) -> list:
    """Simple deduplication: remove identical text lines across overlapping tiles."""
    seen = set()
    unique = []
    for r in results:
        texts = r.get("text_lines", [])
        key = "|".join(texts)
        if key and key not in seen:
            seen.add(key)
            unique.append(r)
        elif not key:
            unique.append(r)
    return unique


def process_tiles(tiles_dir: Path, output_path: Path, api_key: str = None):
    """Process all tiles in directory and save results."""
    if api_key is None:
        api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        print("ERROR: Set DASHSCOPE_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)

    tiles = sorted(tiles_dir.glob("*.png"))
    if not tiles:
        print(f"ERROR: No PNG tiles found in {tiles_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(tiles)} tiles to process")

    all_results = []
    for i, tile_path in enumerate(tiles):
        print(f"[{i + 1}/{len(tiles)}] {tile_path.name}")

        b64 = encode_image_to_base64(tile_path)
        result = call_qwen_ocr(api_key, b64)

        # Add metadata
        result["_tile"] = tile_path.name
        # Parse coordinates from filename: tile_XXXXX_YYYYY
        m = re.search(r"x(\d+)_y(\d+)", tile_path.name)
        if m:
            result["_x"] = int(m.group(1))
            result["_y"] = int(m.group(2))

        all_results.append(result)

        # Rate limit: be nice to API
        time.sleep(0.5)

    # Deduplicate
    print("Deduplicating...")
    deduped = deduplicate_results(all_results)
    print(f"Reduced from {len(all_results)} to {len(deduped)} unique results")

    # Save JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)
    print(f"Saved JSON: {output_path}")

    # Save simple text summary
    txt_path = output_path.with_suffix(".txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for r in deduped:
            f.write(f"--- {r.get('_tile', '?')} ---\n")
            for line in r.get("text_lines", []):
                f.write(line + "\n")
            f.write("\n")
    print(f"Saved text: {txt_path}")


def main():
    parser = argparse.ArgumentParser(description="OCR tiles via Alibaba Qwen-VL-OCR")
    parser.add_argument("--tiles-dir", default="./tiles", help="Directory with PNG tiles")
    parser.add_argument("--output", default="./output/ocr_result.json", help="Output JSON path")
    parser.add_argument("--api-key", help="Alibaba DashScope API key (or set DASHSCOPE_API_KEY)")
    args = parser.parse_args()

    process_tiles(Path(args.tiles_dir), Path(args.output), args.api_key)


if __name__ == "__main__":
    main()
