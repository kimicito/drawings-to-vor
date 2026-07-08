#!/usr/bin/env python3
"""Process all drawing pages (full page, 2000px) to extract quantities."""
import sys, os, json
from pathlib import Path
from collections import defaultdict
from PIL import Image

sys.path.insert(0, '/root/.openclaw/workspace/projects/drawings-to-vor/scripts')
from tile_ocr import load_env, encode_image_to_base64, call_qwen_vision

load_env()

drawings_dir = Path('/root/.openclaw/workspace/projects/drawings-to-vor/batch_kj5/drawings')
tiff_files = sorted(drawings_dir.glob('*.tif'))

api_key = os.environ.get('DASHSCOPE_API_KEY')
base_url = os.environ.get('DASHSCOPE_COMPATIBLE_URL', 'https://ws-tgqwfcamlhhgyuu2.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1')
model = 'qwen-vl-ocr'

prompt = '''На этом инженерном чертеже показана схема расположения конструктивных элементов фундамента.

ЗАДАЧА: Найди ВСЕ марки элементов и посчитай их точное количество.

Ищи марки:
- Рсм1, Рсм2 (ростверки)
- БФм1...БФм17 (балки)
- ФОм1...ФОм5 (фундаменты)
- КП4, КП5, КП6 (каркасы)
- Зд1 (закладные)
- СБН12-450 (сваи)

ВАЖНО: Посмотри на ВЕСЬ чертёж. Если рядом с маркой есть цифра — используй её. Если нет — посчитай элементы на плане.

Верни JSON: {"elements": [{"mark": "Рсм1", "quantity": 13, "type": "rostverk"}]}'''

all_elements = defaultdict(lambda: {'quantity': 0, 'type': '', 'pages': []})

for i, tif_path in enumerate(tiff_files):
    print(f'[{i+1}/{len(tiff_files)}] Processing {tif_path.name}...')
    
    try:
        # Convert TIFF to PNG 2000px
        img = Image.open(tif_path)
        ratio = 2000 / img.width
        new_size = (2000, int(img.height * ratio))
        img_resized = img.resize(new_size, Image.LANCZOS)
        
        png_path = Path('/tmp') / f'{tif_path.stem}_2000.png'
        img_resized.save(png_path, 'PNG')
        
        # Call Qwen-VL
        base64_image = encode_image_to_base64(png_path)
        result = call_qwen_vision(api_key, base_url, model, base64_image, prompt)
        raw_text = result.get('_raw_text', '')
        
        # Parse JSON
        elements = []
        try:
            json_match = raw_text.find('{')
            if json_match >= 0:
                json_str = raw_text[json_match:]
                brace_count = 0
                end_idx = 0
                for j, char in enumerate(json_str):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = j + 1
                            break
                if end_idx > 0:
                    data = json.loads(json_str[:end_idx])
                    elements = data.get('elements', [])
        except Exception as e:
            print(f'  JSON parse error: {e}')
        
        print(f'  Found {len(elements)} elements')
        for elem in elements:
            mark = elem.get('mark', '')
            qty = elem.get('quantity', 0)
            elem_type = elem.get('type', '')
            if mark and qty > 0:
                all_elements[mark]['quantity'] += qty
                all_elements[mark]['type'] = elem_type or all_elements[mark]['type']
                all_elements[mark]['pages'].append(tif_path.name)
        
        # Cleanup
        png_path.unlink(missing_ok=True)
        
    except Exception as e:
        print(f'  ERROR: {e}')

# Save results
output_dir = Path('/root/.openclaw/workspace/projects/drawings-to-vor/batch_kj5/qwen_full_pages')
output_dir.mkdir(exist_ok=True)

aggregated = []
for mark, info in sorted(all_elements.items()):
    aggregated.append({
        'mark': mark,
        'quantity': info['quantity'],
        'type': info['type'],
        'pages_found': len(info['pages'])
    })

with open(output_dir / 'quantities_from_pages.json', 'w', encoding='utf-8') as f:
    json.dump(aggregated, f, ensure_ascii=False, indent=2)

# Print summary
print('\n' + '='*60)
print('AGGREGATED QUANTITIES FROM ALL PAGES:')
print('='*60)
for elem in aggregated:
    print(f"{elem['mark']:<15} {elem['quantity']:<5} {elem['type']:<15} (found in {elem['pages_found']} pages)")
print('='*60)
print(f'Total unique elements: {len(aggregated)}')
print(f'Total pages processed: {len(tiff_files)}')
