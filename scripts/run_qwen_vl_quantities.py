#!/usr/bin/env python3
"""Run Qwen-VL on specific tiles with quantity-extraction prompt."""
import base64
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, '/root/.openclaw/workspace/projects/drawings-to-vor/scripts')
from tile_ocr import load_env, encode_image_to_base64, call_qwen_vision

load_env()

API_KEY = os.environ.get('DASHSCOPE_API_KEY')
BASE_URL = os.environ.get('DASHSCOPE_COMPATIBLE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
MODEL = 'qwen-vl-ocr'

TILES_DIR = Path('/root/.openclaw/workspace/projects/drawings-to-vor/batch_kj5/tiles')
OUTPUT_DIR = Path('/root/.openclaw/workspace/projects/drawings-to-vor/batch_kj5/qwen_vl_quantities')

# Tiles that contain element marks (from previous analysis)
TARGET_TILES = [
    'page01_tile0010_x08780_y00000.png',  # Рсм1
    'page01_tile0010_x08810_y00000.png',  # БФм1
    'page01_tile0043_x02700_y03932.png',  # ФОм1
    'page01_tile0010_x01800_y00900.png',  # КП4
    'page01_tile0033_x05400_y02471.png',  # Зд1
]

QUANTITY_PROMPT = """You are analyzing an engineering construction plan (drawing). 

Look at the image and identify how many of each structural element type are shown. 
Pay attention to numbers near element labels (e.g., "2 шт.", "4", or just numbers near element marks).

Return the data in this JSON format:
{
  "elements": [
    {"mark": "Рсм1", "quantity": 13, "type": "rostverk"},
    {"mark": "БФм1", "quantity": 2, "type": "beam"}
  ]
}

If you cannot determine quantities, return empty array [].
"""

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    
    for tile_name in TARGET_TILES:
        tile_path = TILES_DIR / tile_name
        if not tile_path.exists():
            print(f"SKIP: {tile_name} not found")
            continue
        
        print(f"Processing: {tile_name}")
        b64 = encode_image_to_base64(tile_path)
        
        try:
            response = call_qwen_vision(API_KEY, BASE_URL, MODEL, b64, QUANTITY_PROMPT)
            raw_text = response.get('raw_text', '')
            
            # Try to parse JSON
            parsed = {}
            if '```json' in raw_text:
                json_match = raw_text.split('```json')[1].split('```')[0]
                parsed = json.loads(json_match)
            elif '```' in raw_text:
                json_match = raw_text.split('```')[1].split('```')[0]
                parsed = json.loads(json_match)
            else:
                try:
                    parsed = json.loads(raw_text)
                except:
                    pass
            
            result = {
                'tile': tile_name,
                'raw_text': raw_text,
                'parsed': parsed
            }
            results.append(result)
            
            print(f"  Result: {parsed}")
            
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({'tile': tile_name, 'error': str(e)})
    
    # Save results
    output_path = OUTPUT_DIR / 'qwen_vl_results.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved: {output_path}")

if __name__ == '__main__':
    main()
