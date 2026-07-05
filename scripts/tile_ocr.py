#!/usr/bin/env python3
"""
tile_ocr.py — Send tiles to vision API (Mistral Pixtral or Alibaba Qwen-VL-OCR)
and collect structured text/tables/dimensions.

Features:
- Base64 encoding (no external upload needed)
- Retry with exponential backoff
- Deduplication by overlap area
- Structured output: text, dimensions, tables, labels
- Outputs JSON + TXT + CSV

Usage:
    # Mistral (default)
    export MISTRAL_API_KEY=mk-xxx
    python tile_ocr.py --tiles-dir ./tiles/ --output result.json

    # Alibaba Qwen-VL-OCR
    export DASHSCOPE_API_KEY=sk-xxx
    export DASHSCOPE_COMPATIBLE_URL=https://xxx.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1
    python tile_ocr.py --provider qwen --model qwen-vl-ocr --tiles-dir ./tiles/ --output result.json

    # Alibaba Qwen-VL-Max (better understanding)
    python tile_ocr.py --provider qwen --model qwen-vl-max --tiles-dir ./tiles/ --output result.json
"""

import argparse
import base64
import json
import os
import re
import sys
import time
from pathlib import Path


def load_env():
    """Load .env file if exists."""
    env_file = Path("/root/.openclaw/workspace/.env")
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key, val)


def encode_image_to_base64(image_path: Path) -> str:
    """Read image and return base64 data URI."""
    with open(image_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("utf-8")
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
                "_provider": "mistral",
                "_model": "pixtral-12b-2409",
            }
        except Exception as e:
            print(f"  API error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return {"_error": str(e), "text_lines": [], "dimensions": [], "tables": [], "codes": [], "geology": [], "_provider": "mistral"}


def call_qwen_vision(api_key: str, base_url: str, model: str, base64_image: str, prompt: str = None) -> dict:
    """Call Alibaba Qwen-VL API. Returns parsed response."""
    import urllib.request
    import urllib.error

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

    payload = {
        "model": model,
        "messages": [
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
        ],
        "max_tokens": 4096,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    max_retries = 3
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode("utf-8"))

                if "choices" in result and result["choices"]:
                    content = result["choices"][0].get("message", {}).get("content", "")
                    usage = result.get("usage", {})
                    return {
                        "_raw_text": content,
                        "text_lines": extract_section(content, "TEXT_LINES"),
                        "dimensions": extract_section(content, "DIMENSIONS"),
                        "tables": extract_section(content, "TABLES"),
                        "codes": extract_section(content, "CODES"),
                        "geology": extract_section(content, "GEOLOGY"),
                        "_tokens": usage.get("total_tokens"),
                        "_prompt_tokens": usage.get("prompt_tokens"),
                        "_completion_tokens": usage.get("completion_tokens"),
                        "_provider": "qwen",
                        "_model": model,
                    }
                else:
                    return {"_error": f"Unexpected response: {result}", "text_lines": [], "dimensions": [], "tables": [], "codes": [], "geology": [], "_provider": "qwen", "_model": model}
        except urllib.error.HTTPError as e:
            error_msg = f"HTTP {e.code}: {e.reason}"
            try:
                body = json.loads(e.read().decode())
                error_msg += f" - {body.get('error', {}).get('message', '')}"
            except:
                pass
            print(f"  API error (attempt {attempt + 1}/{max_retries}): {error_msg}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return {"_error": error_msg, "text_lines": [], "dimensions": [], "tables": [], "codes": [], "geology": [], "_provider": "qwen", "_model": model}
        except Exception as e:
            print(f"  API error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return {"_error": str(e), "text_lines": [], "dimensions": [], "tables": [], "codes": [], "geology": [], "_provider": "qwen", "_model": model}


def extract_json_from_markdown(text: str) -> dict:
    """Extract JSON from markdown code blocks (```json ... ```)."""
    import json
    # Find ```json blocks
    import re
    pattern = r'```json\s*(\{.*?\})\s*```'
    matches = re.findall(pattern, text, re.DOTALL)
    if matches:
        try:
            return json.loads(matches[0])
        except json.JSONDecodeError:
            pass
    # Try without json label
    pattern2 = r'```\s*(\{.*?\})\s*```'
    matches2 = re.findall(pattern2, text, re.DOTALL)
    if matches2:
        try:
            return json.loads(matches2[0])
        except json.JSONDecodeError:
            pass
    # Try raw JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    return {}


def extract_section(text: str, section_name: str) -> list:
    """Extract lines from a section like 'TEXT_LINES:' to next section or end.
    Also handles JSON markdown output from Qwen (keys in UPPERCASE)."""
    # First try JSON parsing (for Qwen markdown output)
    json_data = extract_json_from_markdown(text)
    if json_data:
        # Qwen returns UPPERCASE keys: TEXT_LINES, DIMENSIONS, etc.
        key_map = {
            "TEXT_LINES": ["text_lines", "TEXT_LINES"],
            "DIMENSIONS": ["dimensions", "DIMENSIONS"],
            "TABLES": ["tables", "TABLES"],
            "CODES": ["codes", "CODES"],
            "GEOLOGY": ["geology", "GEOLOGY"],
        }
        possible_keys = key_map.get(section_name, [section_name.lower(), section_name])
        for json_key in possible_keys:
            if json_key in json_data:
                val = json_data[json_key]
                if isinstance(val, list):
                    return val
                elif isinstance(val, str):
                    return [val] if val else []
    
    # Fallback to text parsing (for Mistral plain text output)
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


def process_tiles(tiles_dir: Path, output_path: Path, provider: str = "mistral", model: str = None, api_key: str = None, base_url: str = None):
    """Process all tiles in directory and save results."""
    
    if provider == "mistral":
        if api_key is None:
            api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            print("ERROR: Set MISTRAL_API_KEY environment variable or --api-key", file=sys.stderr)
            sys.exit(1)
        model_name = model or "pixtral-12b-2409"
        call_fn = call_mistral_vision
        rate_limit_delay = 0.5
        
    elif provider == "qwen":
        if api_key is None:
            api_key = os.environ.get("DASHSCOPE_API_KEY")
        if not api_key:
            print("ERROR: Set DASHSCOPE_API_KEY environment variable or --api-key", file=sys.stderr)
            sys.exit(1)
        if base_url is None:
            base_url = os.environ.get("DASHSCOPE_COMPATIBLE_URL")
        if not base_url:
            print("ERROR: Set DASHSCOPE_COMPATIBLE_URL environment variable or --base-url", file=sys.stderr)
            sys.exit(1)
        model_name = model or "qwen-vl-ocr"
        call_fn = lambda key, img, prompt=None: call_qwen_vision(key, base_url, model_name, img, prompt)
        rate_limit_delay = 1.0  # Qwen has stricter rate limits
        
    else:
        print(f"ERROR: Unknown provider '{provider}'. Use 'mistral' or 'qwen'.", file=sys.stderr)
        sys.exit(1)

    tiles = sorted(tiles_dir.glob("*.png"))
    if not tiles:
        print(f"ERROR: No PNG tiles found in {tiles_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Provider: {provider}, Model: {model_name}")
    print(f"Found {len(tiles)} tiles to process")

    all_results = []
    total_tokens = 0
    errors = 0
    
    for i, tile_path in enumerate(tiles):
        print(f"[{i + 1}/{len(tiles)}] {tile_path.name}")

        b64 = encode_image_to_base64(tile_path)
        result = call_fn(api_key, b64)

        # Add metadata
        result["_tile"] = tile_path.name
        result["_provider"] = provider
        result["_model"] = model_name
        
        # Parse coordinates from filename: tile_XXXXX_YYYYY
        m = re.search(r"x(\d+)_y(\d+)", tile_path.name)
        if m:
            result["_x"] = int(m.group(1))
            result["_y"] = int(m.group(2))

        if result.get("_error"):
            errors += 1
        total_tokens += result.get("_tokens", 0) or 0
        all_results.append(result)

        # Rate limit
        time.sleep(rate_limit_delay)

    # Deduplicate
    print("Deduplicating...")
    deduped = deduplicate_results(all_results)
    print(f"Reduced from {len(all_results)} to {len(deduped)} unique results")
    print(f"Total tokens used: {total_tokens}")
    print(f"Errors: {errors}/{len(tiles)}")

    # Save JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)
    print(f"Saved JSON: {output_path}")

    # Save simple text summary
    txt_path = output_path.with_suffix(".txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for r in deduped:
            f.write(f"--- {r.get('_tile', '?')} [{r.get('_provider', '?')}] ---\n")
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
        f.write("tile,x,y,provider,model,text_lines,dimensions,codes,geology\n")
        for r in deduped:
            tile = r.get("_tile", "")
            x = r.get("_x", "")
            y = r.get("_y", "")
            prov = r.get("_provider", "")
            mod = r.get("_model", "")
            texts = " | ".join(r.get("text_lines", []))
            dims = " | ".join(r.get("dimensions", []))
            codes = " | ".join(r.get("codes", []))
            geo = " | ".join(r.get("geology", []))
            f.write(f'"{tile}",{x},{y},{prov},{mod},"{texts}","{dims}","{codes}","{geo}"\n')
    print(f"Saved CSV: {csv_path}")


def main():
    parser = argparse.ArgumentParser(description="OCR tiles via Mistral or Qwen-VL")
    parser.add_argument("--tiles-dir", default="./tiles", help="Directory with PNG tiles")
    parser.add_argument("--output", default="./output/ocr_result.json", help="Output JSON path")
    parser.add_argument("--provider", default="mistral", choices=["mistral", "qwen"], help="API provider")
    parser.add_argument("--model", help="Model name (default: pixtral-12b-2409 for mistral, qwen-vl-ocr for qwen)")
    parser.add_argument("--api-key", help="API key (or use env var)")
    parser.add_argument("--base-url", help="Base URL for API (only for qwen)")
    args = parser.parse_args()

    load_env()
    process_tiles(Path(args.tiles_dir), Path(args.output), args.provider, args.model, args.api_key, args.base_url)


if __name__ == "__main__":
    main()
