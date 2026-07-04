#!/usr/bin/env python3
"""
tile_ocr.py — Send tiles to Mistral Pixtral and collect structured text/tables/dimensions.

Features:
- Base64 encoding (no external upload needed)
- Retry with exponential backoff
- Deduplication by overlap area
- Structured output: text, dimensions, tables, labels
- Outputs JSON + TXT + CSV

Usage:
    export MISTRAL_API_KEY=mk-xxx
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


def call_mistral_vision(api_key: str, base64_image: str, prompt: str = None) -> dict:
    """Call Mistral Pixtral API. Returns parsed response."""
    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: install 'openai' package: pip install openai", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.mistral.ai/v1",
    )

    default_prompt = (
        "Extract all information from this engineering drawing fragment. "
        "Return structured data in this format:\n\n"
        "TEXT_LINES: List all text lines found (labels, notes, titles).\n"
        "DIMENSIONS: List all dimension numbers with units (e.g., '416 mm', '380.7').\n"
        "TABLES: List any table rows or cells visible.\n"
        "CODES: List any codes, standards, or references (e.g., 'ГОСТ 1221330.2016').\n"
        "GEOLOGY: List any geological markers (e.g., 'QIV', 'C-26').\n"
        "\nIf nothing found, write 'No text found'."
    )

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": base64_image},
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
                model="pixtral-12b-2409",
                messages=messages,
                max_tokens=800,
            )
            content = completion.choices[0].message.content
            return {
                "_raw_text": content,
                "text_lines": extract_section(content, "TEXT_LINES"),
                "dimensions": extract_section(content, "DIMENSIONS"),
                "tables": extract_section(content, "TABLES"),
                "codes": extract_section(content, "CODES"),
                "geology": extract_section(content, "GEOLOGY"),
                "_tokens": completion.usage.total_tokens if completion.usage else None,
            }
        except Exception as e:
            print(f"  API error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return {"_error": str(e), "text_lines": [], "dimensions": [], "tables": [], "codes": [], "geology": []}


def extract_section(text: str, section_name: str) -> list:
    """Extract lines from a section like 'TEXT_LINES:' to next section or end."""
    lines = text.split('\n')
    result = []
    in_section = False
    for line in lines:
        if line.strip().startswith(section_name + ':'):
            in_section = True
            continue
        if in_section:
            if any(line.strip().startswith(s + ':') for s in ['TEXT_LINES', 'DIMENSIONS', 'TABLES', 'CODES', 'GEOLOGY']):
                break
            if line.strip() and not line.strip().startswith('---'):
                result.append(line.strip().lstrip('- ').strip())
    return result


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
        api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("ERROR: Set MISTRAL_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)

    tiles = sorted(tiles_dir.glob("*.png"))
    if not tiles:
        print(f"ERROR: No PNG tiles found in {tiles_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(tiles)} tiles to process")

    all_results = []
    total_tokens = 0
    for i, tile_path in enumerate(tiles):
        print(f"[{i + 1}/{len(tiles)}] {tile_path.name}")

        b64 = encode_image_to_base64(tile_path)
        result = call_mistral_vision(api_key, b64)

        # Add metadata
        result["_tile"] = tile_path.name
        # Parse coordinates from filename: tile_XXXXX_YYYYY
        m = re.search(r"x(\d+)_y(\d+)", tile_path.name)
        if m:
            result["_x"] = int(m.group(1))
            result["_y"] = int(m.group(2))

        total_tokens += result.get("_tokens", 0) or 0
        all_results.append(result)

        # Rate limit: be nice to API
        time.sleep(0.5)

    # Deduplicate
    print("Deduplicating...")
    deduped = deduplicate_results(all_results)
    print(f"Reduced from {len(all_results)} to {len(deduped)} unique results")
    print(f"Total tokens used: {total_tokens}")

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
            f.write(f"TEXT: {r.get('text_lines', [])}\n")
            f.write(f"DIMS: {r.get('dimensions', [])}\n")
            f.write(f"CODES: {r.get('codes', [])}\n")
            f.write(f"GEO: {r.get('geology', [])}\n")
            f.write(f"RAW: {r.get('_raw_text', '')[:200]}\n")
            f.write("\n")
    print(f"Saved text: {txt_path}")

    # Save CSV with coordinates
    csv_path = output_path.with_suffix(".csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("tile,x,y,text_lines,dimensions,codes,geology\n")
        for r in deduped:
            tile = r.get("_tile", "")
            x = r.get("_x", "")
            y = r.get("_y", "")
            texts = " | ".join(r.get("text_lines", []))
            dims = " | ".join(r.get("dimensions", []))
            codes = " | ".join(r.get("codes", []))
            geo = " | ".join(r.get("geology", []))
            f.write(f'"{tile}",{x},{y},"{texts}","{dims}","{codes}","{geo}"\n')
    print(f"Saved CSV: {csv_path}")


def main():
    parser = argparse.ArgumentParser(description="OCR tiles via Mistral Pixtral")
    parser.add_argument("--tiles-dir", default="./tiles", help="Directory with PNG tiles")
    parser.add_argument("--output", default="./output/ocr_result.json", help="Output JSON path")
    parser.add_argument("--api-key", help="Mistral API key (or set MISTRAL_API_KEY)")
    args = parser.parse_args()

    process_tiles(Path(args.tiles_dir), Path(args.output), args.api_key)


if __name__ == "__main__":
    main()
