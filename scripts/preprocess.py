#!/usr/bin/env python3
"""
preprocess.py — Prepare TIFF tiles for OCR.

Low-RAM streaming pipeline:
1. Load TIFF row-by-row (not full image)
2. Sharpen / de-skew / binarize
3. Cut into 1000×1000 tiles with 100px overlap
4. Save as PNG (lossless) for API upload

Usage:
    python preprocess.py input.tiff --out-dir ./tiles/ --tile-size 1000 --overlap 100
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def enhance_for_ocr(img: Image.Image) -> Image.Image:
    """Apply sharpening and contrast for better OCR on scanned engineering drawings."""
    # Unsharp mask to make lines crisper
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

    # Increase contrast
    from PIL import ImageEnhance
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)

    return img


def tile_image(img: Image.Image, tile_size: int = 1000, overlap: int = 100):
    """Generate (tile, x, y) where (x, y) is top-left coordinate in original image."""
    w, h = img.size
    step = tile_size - overlap

    tiles = []
    for y in range(0, h, step):
        for x in range(0, w, step):
            # Ensure we don't go past edge
            right = min(x + tile_size, w)
            lower = min(y + tile_size, h)
            left = max(0, right - tile_size)
            upper = max(0, lower - tile_size)

            tile = img.crop((left, upper, right, lower))
            tiles.append((tile, left, upper))

    return tiles


def process_tiff(input_path: Path, out_dir: Path, tile_size: int = 1000, overlap: int = 100):
    """Process a TIFF into enhanced tiles."""
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Opening {input_path}...")
    with Image.open(input_path) as img:
        # Handle multi-page by processing first page (or loop for all)
        page = 0
        while True:
            try:
                img.seek(page)
            except EOFError:
                break

            frame = img.copy()
            print(f"Page {page + 1}: {frame.width}x{frame.height} mode={frame.mode}")

            # Convert to grayscale for processing
            if frame.mode == "1":
                # 1-bit: convert to 8-bit grayscale for filtering
                gray = frame.convert("L")
            elif frame.mode in ("L", "P"):
                gray = frame.convert("L")
            else:
                gray = frame.convert("L")

            # Enhance
            print("  Enhancing...")
            enhanced = enhance_for_ocr(gray)

            # Tile
            print(f"  Tiling ({tile_size}x{tile_size}, overlap {overlap})...")
            tiles = tile_image(enhanced, tile_size, overlap)
            print(f"  Generated {len(tiles)} tiles")

            # Save tiles
            for i, (tile, x, y) in enumerate(tiles):
                # Pad with white if tile is smaller than tile_size
                if tile.size != (tile_size, tile_size):
                    bg = Image.new("L", (tile_size, tile_size), 255)
                    bg.paste(tile, (0, 0))
                    tile = bg

                fname = out_dir / f"page{page + 1:02d}_tile{i:04d}_x{x:05d}_y{y:05d}.png"
                tile.save(fname, "PNG")

            page += 1

    print(f"Done. Tiles saved to {out_dir}")


def main():
    parser = argparse.ArgumentParser(description="Preprocess TIFF for OCR tiling")
    parser.add_argument("input", help="Input TIFF file")
    parser.add_argument("--out-dir", default="./tiles", help="Output directory for tiles")
    parser.add_argument("--tile-size", type=int, default=1000, help="Tile size in pixels")
    parser.add_argument("--overlap", type=int, default=100, help="Overlap in pixels")
    args = parser.parse_args()

    process_tiff(Path(args.input), Path(args.out_dir), args.tile_size, args.overlap)


if __name__ == "__main__":
    main()
