#!/usr/bin/env python3
"""
run_pipeline.py — Unified TIFF → ВОР pipeline with automated review.

Chains: preprocess → tile_ocr → extract_vor → vor_reviewer

Usage:
    python scripts/run_pipeline.py \
      --tiff drawing.tiff \
      --output-dir ./output \
      --tile-size 1000 --overlap 100
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_step(name: str, cmd: list, cwd: Path = None) -> bool:
    """Run a pipeline step and report result."""
    print(f"\n{'='*60}")
    print(f"STEP: {name}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=False)
    if result.returncode != 0:
        print(f"❌ STEP FAILED: {name}")
        return False
    print(f"✅ STEP COMPLETED: {name}")
    return True


def main():
    parser = argparse.ArgumentParser(description='TIFF → ВОР pipeline')
    parser.add_argument('--tiff', required=True, help='Input TIFF file')
    parser.add_argument('--output-dir', default='./output', help='Output directory')
    parser.add_argument('--tile-size', type=int, default=1000, help='Tile size')
    parser.add_argument('--overlap', type=int, default=100, help='Tile overlap')
    parser.add_argument('--skip-pdf', action='store_true', help='Skip PDF conversion')
    parser.add_argument('--skip-ocr', action='store_true', help='Skip OCR (use existing)')
    args = parser.parse_args()
    
    tiff_path = Path(args.tiff).resolve()
    output_dir = Path(args.output_dir).resolve()
    tiles_dir = output_dir / 'tiles'
    
    if not tiff_path.exists():
        print(f"ERROR: TIFF not found: {tiff_path}", file=sys.stderr)
        sys.exit(1)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    tiles_dir.mkdir(exist_ok=True)
    
    project_root = Path(__file__).parent.parent
    scripts_dir = project_root / 'scripts'
    
    steps_completed = 0
    total_steps = 4
    
    # Step 1: Preprocess (TIFF → tiles)
    if not args.skip_ocr:
        if not run_step("Preprocess (TIFF → tiles)", [
            sys.executable, str(scripts_dir / 'preprocess.py'),
            str(tiff_path),
            '--out-dir', str(tiles_dir),
            '--tile-size', str(args.tile_size),
            '--overlap', str(args.overlap)
        ]):
            sys.exit(1)
        steps_completed += 1
        
        # Step 2: OCR (tiles → JSON)
        ocr_json = output_dir / 'ocr_result.json'
        if not run_step("OCR (Qwen-VL)", [
            sys.executable, str(scripts_dir / 'tile_ocr.py'),
            '--model', 'qwen-vl-ocr',
            '--tiles-dir', str(tiles_dir),
            '--output', str(ocr_json)
        ]):
            sys.exit(1)
        steps_completed += 1
    else:
        ocr_json = output_dir / 'ocr_result.json'
        if not ocr_json.exists():
            print(f"ERROR: --skip-ocr but no existing OCR: {ocr_json}", file=sys.stderr)
            sys.exit(1)
        print(f"\n{'='*60}")
        print("SKIP: Using existing OCR")
        print(f"{'='*60}")
        steps_completed += 2
    
    # Step 3: Extract ВОР
    vor_csv = output_dir / 'vor.csv'
    if not run_step("Extract ВОР", [
        sys.executable, str(scripts_dir / 'extract_vor_final.py'),
        '--ocr-json', str(ocr_json),
        '--output', str(vor_csv.with_suffix(''))
    ]):
        sys.exit(1)
    steps_completed += 1
    
    # Step 4: Review ВОР
    review_json = output_dir / 'vor_review.json'
    if not run_step("Review ВОР", [
        sys.executable, str(scripts_dir / 'vor_reviewer.py'),
        '--ocr-json', str(ocr_json),
        '--vor-csv', str(vor_csv),
        '--output', str(review_json)
    ]):
        sys.exit(1)
    steps_completed += 1
    
    # Final summary
    print(f"\n{'='*60}")
    print(f"PIPELINE COMPLETE: {steps_completed}/{total_steps} steps")
    print(f"{'='*60}")
    print(f"Output directory: {output_dir}")
    print(f"  OCR:     {ocr_json}")
    print(f"  ВОР:     {vor_csv}")
    print(f"  Review:  {review_json}")
    print(f"{'='*60}")
    
    # Load and display review result
    try:
        import json
        with open(review_json, 'r') as f:
            review = json.load(f)
        status = review.get('status', 'UNKNOWN')
        score = review.get('score', 0)
        print(f"\nВОР Review: {status} ({score}%)")
        if status == 'FAIL':
            print("⚠️  Please check issues and re-run if needed.")
            sys.exit(2)
        else:
            print("✅ ВОР validated successfully!")
    except Exception as e:
        print(f"⚠️  Could not load review: {e}")


if __name__ == '__main__':
    main()
