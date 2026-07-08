#!/usr/bin/env bash
# batch_remaining.sh — обработка оставшихся 15 чертежей

set -e

FILES=(
  drawing_new5 drawing_new6 drawing_new7 drawing_new8 drawing_new9
  drawing_new11 drawing_new13 drawing_new14 drawing_new15
  drawing_new16 drawing_new17 drawing_new18 drawing_new19 drawing_new20 drawing_new21
)

for f in "${FILES[@]}"; do
  echo "=== Processing $f ==="
  
  # Step 1: Preprocess
  python3 /root/.openclaw/workspace/projects/drawings-to-vor/scripts/preprocess.py \
    /root/.openclaw/workspace/projects/drawings-to-vor/samples/${f}.tiff \
    --out-dir /root/.openclaw/workspace/projects/drawings-to-vor/tiles_${f} \
    --tile-size 1000
  
  # Step 2: OCR
  python3 /root/.openclaw/workspace/projects/drawings-to-vor/scripts/tile_ocr.py \
    --model qwen-vl-ocr \
    --tiles-dir /root/.openclaw/workspace/projects/drawings-to-vor/tiles_${f} \
    --output /root/.openclaw/workspace/projects/drawings-to-vor/ocr_${f}.json
  
  echo "=== $f DONE ==="
  echo ""
done

echo "ALL 15 FILES COMPLETE!"
