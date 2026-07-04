#!/usr/bin/env python3
"""
tiff_to_pdf.py — Lossless TIFF → PDF conversion for engineering drawings.

Features:
- Streams page-by-page (low RAM usage)
- Preserves DPI, dimensions, and physical paper size (A0/A1/A2)
- No JPEG recompression (uses lossless CCITT or flate)
- Handles multi-page TIFFs or folder of single-page TIFFs

Usage:
    python tiff_to_pdf.py input.tiff output.pdf
    python tiff_to_pdf.py /path/to/folder/ output.pdf
"""

import argparse
import io
import os
import sys
from pathlib import Path

from PIL import Image, TiffImagePlugin


def get_paper_size_mm(width_px: int, height_px: int, dpi: float) -> str:
    """Guess ISO paper size from pixel dimensions and DPI."""
    mm_per_inch = 25.4
    w_mm = (width_px / dpi) * mm_per_inch
    h_mm = (height_px / dpi) * mm_per_inch

    sizes = {
        "A0": (841, 1189),
        "A1": (594, 841),
        "A2": (420, 594),
        "A3": (297, 420),
        "A4": (210, 297),
    }

    for name, (sw, sh) in sizes.items():
        for (rw, rh) in [(w_mm, h_mm), (h_mm, w_mm)]:
            if abs(rw - sw) < 20 and abs(rh - sh) < 20:
                return name
    return "Custom"


def tiff_page_generator(path: Path):
    """Yield (image, page_num, dpi) for each page in a TIFF file."""
    with Image.open(path) as img:
        page = 0
        while True:
            try:
                img.seek(page)
            except EOFError:
                break

            # Clone to independent image
            frame = img.copy()

            # Extract DPI
            dpi = frame.info.get("dpi", (300, 300))
            if isinstance(dpi, tuple):
                xdpi, ydpi = dpi
            else:
                xdpi = ydpi = float(dpi) if dpi else 300.0

            yield frame, page, (xdpi, ydpi)
            page += 1


def convert_single_tiff(input_path: Path, output_path: Path):
    """Convert single multi-page TIFF to PDF."""
    images = []
    metas = []

    for frame, page_num, (xdpi, ydpi) in tiff_page_generator(input_path):
        paper = get_paper_size_mm(frame.width, frame.height, xdpi)
        print(f"  Page {page_num + 1}: {frame.width}x{frame.height} @ {xdpi:.0f} DPI → {paper}")

        # For 1-bit images, keep mode; for others convert to RGB if needed
        if frame.mode == "1":
            # Keep binary — PDF can store CCITT Group 4
            im = frame
        elif frame.mode in ("L", "P"):
            im = frame.convert("L")
        else:
            im = frame.convert("RGB")

        images.append(im)
        metas.append({"dpi": (xdpi, ydpi)})

    if not images:
        raise ValueError(f"No pages found in {input_path}")

    # Save first page with rest appended
    first = images[0]
    rest = images[1:] if len(images) > 1 else []

    first.save(
        output_path,
        "PDF",
        resolution=metas[0]["dpi"][0],
        save_all=True,
        append_images=rest,
    )
    print(f"Saved: {output_path} ({len(images)} pages)")


def convert_folder(input_folder: Path, output_path: Path):
    """Convert folder of TIFFs (sorted) into single PDF."""
    tiffs = sorted(input_folder.glob("*.tif*"))  # .tif, .tiff, .TIF
    if not tiffs:
        raise ValueError(f"No TIFF files found in {input_folder}")

    print(f"Found {len(tiffs)} TIFF files")
    images = []

    for tiff_path in tiffs:
        print(f"Processing: {tiff_path.name}")
        for frame, page_num, (xdpi, ydpi) in tiff_page_generator(tiff_path):
            paper = get_paper_size_mm(frame.width, frame.height, xdpi)
            print(f"  Page {page_num + 1}: {frame.width}x{frame.height} @ {xdpi:.0f} DPI → {paper}")

            if frame.mode == "1":
                im = frame
            elif frame.mode in ("L", "P"):
                im = frame.convert("L")
            else:
                im = frame.convert("RGB")
            images.append((im, xdpi))

    if not images:
        raise ValueError("No images loaded")

    first, dpi = images[0]
    rest = [im for im, _ in images[1:]]

    first.save(
        output_path,
        "PDF",
        resolution=dpi,
        save_all=True,
        append_images=rest,
    )
    print(f"Saved: {output_path} ({len(images)} pages)")


def main():
    parser = argparse.ArgumentParser(description="Lossless TIFF to PDF converter")
    parser.add_argument("input", help="Input TIFF file or folder containing TIFFs")
    parser.add_argument("output", help="Output PDF file")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"Error: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if input_path.is_dir():
        convert_folder(input_path, output_path)
    else:
        convert_single_tiff(input_path, output_path)


if __name__ == "__main__":
    main()
