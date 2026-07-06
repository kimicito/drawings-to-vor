#!/usr/bin/env python3
"""
batch_process.py — Batch обработка всех TIFF чертежей в папке.

Usage:
    python scripts/batch_process.py --samples-dir ./samples/ --output-dir ./output/
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description, timeout=300):
    """Run a shell command and report."""
    print(f"\n{'='*60}")
    print(f"📋 {description}")
    print(f"Command: {cmd}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr and "error" in result.stderr.lower():
        print(f"STDERR: {result.stderr}", file=sys.stderr)
    
    return result.returncode == 0


def process_tiff(tiff_path: Path, output_dir: Path, scripts_dir: Path):
    """Process a single TIFF through the full pipeline."""
    base_name = tiff_path.stem
    pdf_path = output_dir / f"{base_name}.pdf"
    tiles_dir = output_dir / f"tiles_{base_name}"
    ocr_json = output_dir / f"{base_name}_ocr.json"
    
    print(f"\n🔷 Processing: {tiff_path.name}")
    
    # Step 1: TIFF → PDF
    if not run_command(
        f"python3 {scripts_dir}/tiff_to_pdf.py {tiff_path} {pdf_path}",
        f"Step 1: {tiff_path.name} → PDF"
    ):
        print(f"❌ PDF conversion failed for {tiff_path.name}")
        return False
    
    # Step 2: Preprocess → tiles
    if not run_command(
        f"python3 {scripts_dir}/preprocess.py {tiff_path} --out-dir {tiles_dir} --tile-size 1000 --overlap 100",
        f"Step 2: {tiff_path.name} → Tiles",
        timeout=120
    ):
        print(f"❌ Preprocessing failed for {tiff_path.name}")
        return False
    
    # Step 3: OCR
    env_vars = ""
    if os.environ.get("DASHSCOPE_API_KEY"):
        env_vars = f"DASHSCOPE_API_KEY={os.environ.get('DASHSCOPE_API_KEY')} DASHSCOPE_COMPATIBLE_URL={os.environ.get('DASHSCOPE_COMPATIBLE_URL', '')} "
    
    if not run_command(
        f"{env_vars}python3 {scripts_dir}/tile_ocr.py --model qwen-vl-ocr --tiles-dir {tiles_dir} --output {ocr_json}",
        f"Step 3: {tiff_path.name} → OCR",
        timeout=900
    ):
        print(f"❌ OCR failed for {tiff_path.name}")
        return False
    
    print(f"✅ Completed: {tiff_path.name}")
    return True


def merge_results(output_dir: Path, all_results: list):
    """Merge all OCR results into one JSON."""
    merged = {
        "source_files": [],
        "results": []
    }
    
    for result in all_results:
        json_path = output_dir / f"{result['base_name']}_ocr.json"
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            merged["source_files"].append({
                "file": result['file_name'],
                "base_name": result['base_name'],
                "records": len(data)
            })
            merged["results"].extend(data)
    
    merged_path = output_dir / "merged_ocr_results.json"
    with open(merged_path, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"📦 MERGED RESULTS")
    print(f"{'='*60}")
    print(f"Saved: {merged_path}")
    print(f"Total files: {len(merged['source_files'])}")
    print(f"Total records: {len(merged['results'])}")
    
    return merged


def main():
    parser = argparse.ArgumentParser(description="Batch process TIFF drawings")
    parser.add_argument("--samples-dir", default="./samples", help="Directory with TIFF files")
    parser.add_argument("--output-dir", default="./output", help="Output directory")
    parser.add_argument("--scripts-dir", default="./scripts", help="Scripts directory")
    args = parser.parse_args()
    
    samples_dir = Path(args.samples_dir)
    output_dir = Path(args.output_dir)
    scripts_dir = Path(args.scripts_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all TIFF files
    tiff_files = sorted(samples_dir.glob("*.tiff")) + sorted(samples_dir.glob("*.tif"))
    
    if not tiff_files:
        print(f"ERROR: No TIFF files found in {samples_dir}")
        sys.exit(1)
    
    print(f"{'='*60}")
    print(f"🚀 BATCH PROCESSING: {len(tiff_files)} files")
    print(f"{'='*60}")
    
    all_results = []
    success_count = 0
    
    for i, tiff_path in enumerate(tiff_files, 1):
        print(f"\n\n{'#'*60}")
        print(f"# [{i}/{len(tiff_files)}] {tiff_path.name}")
        print(f"{'#'*60}")
        
        if process_tiff(tiff_path, output_dir, scripts_dir):
            all_results.append({
                "file_name": tiff_path.name,
                "base_name": tiff_path.stem
            })
            success_count += 1
    
    # Merge results
    if all_results:
        merge_results(output_dir, all_results)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    print(f"Total files: {len(tiff_files)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(tiff_files) - success_count}")
    print(f"Output: {output_dir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
