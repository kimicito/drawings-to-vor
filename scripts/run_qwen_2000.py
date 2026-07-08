#!/usr/bin/env python3
"""Run Qwen-VL on all 2000x2000 tiles to extract quantities."""
import sys, os, json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, '/root/.openclaw/workspace/projects/drawings-to-vor/scripts')
from tile_ocr import load_env, encode_image_to_base64, call_qwen_vision

load_env()

tiles_dir = Path('/root/.openclaw/workspace/projects/drawings-to-vor/batch_kj5/tiles_2000')
tiles = sorted(tiles_dir.glob('*.png'))

api_key = os.environ.get('DASHSCOPE_API_KEY')
base_url = os.environ.get('DASHSCOPE_COMPATIBLE_URL', 'https://ws-tgqwfcamlhhgyuu2.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1')
model = 'qwen-vl-ocr'

prompt = '''На этом фрагменте инженерного чертежа показана схема расположения конструктивных элементов (фундаменты, ростверки, балки, сваи, каркасы, закладные детали).

ВАЖНО: Посчитай точное количество каждой марки элементов. Если видишь одинаковые марки в нескольких местах — посчитай все.

Ищи марки: Рсм1, Рсм2, БФм1, БФм2, БФм3, БФм4, БФм5, БФм6, БФм7, БФм8, БФм9, БФм10, БФм11, БФм12, БФм13, БФм14, БФм15, БФм16, БФм17, ФОм1, ФОм2, ФОм3, ФОм4, ФОм5, КП4, КП5, КП6, Зд1, СБН12-450.

Верни JSON: {"elements": [{"mark": "Рсм1", "quantity": 13, "type": "rostverk"}]}'''

results = []
all_elements = defaultdict(lambda: {'quantity': 0, 'type': '', 'tiles': []})

for i, tile_path in enumerate(tiles):
    print(f'[{i+1}/{len(tiles)}] Processing {tile_path.name}...')
    try:
        base64_image = encode_image_to_base64(tile_path)
        result = call_qwen_vision(api_key, base_url, model, base64_image, prompt)
        raw_text = result.get('_raw_text', '')
        
        # Parse JSON from response
        elements = []
        try:
            # Try to find JSON in response
            json_match = raw_text.find('{')
            if json_match >= 0:
                json_str = raw_text[json_match:]
                # Find matching brace
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
            elements = []
        
        print(f'  Found {len(elements)} elements')
        for elem in elements:
            mark = elem.get('mark', '')
            qty = elem.get('quantity', 0)
            elem_type = elem.get('type', '')
            if mark:
                # Only update if this tile hasn't seen this mark before
                if tile_path.name not in all_elements[mark]['tiles']:
                    all_elements[mark]['quantity'] += qty
                    all_elements[mark]['type'] = elem_type or all_elements[mark]['type']
                    all_elements[mark]['tiles'].append(tile_path.name)
        
        results.append({
            'tile': tile_path.name,
            'elements': elements,
            'tokens': result.get('_tokens')
        })
        
    except Exception as e:
        print(f'  ERROR: {e}')
        results.append({'tile': tile_path.name, 'error': str(e)})

# Save results
output_dir = Path('/root/.openclaw/workspace/projects/drawings-to-vor/batch_kj5/qwen_2000')
output_dir.mkdir(exist_ok=True)

with open(output_dir / 'qwen_2000_raw.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

# Save aggregated
aggregated = []
for mark, info in sorted(all_elements.items()):
    aggregated.append({
        'mark': mark,
        'quantity': info['quantity'],
        'type': info['type'],
        'tiles_seen': len(info['tiles'])
    })

with open(output_dir / 'qwen_2000_aggregated.json', 'w', encoding='utf-8') as f:
    json.dump(aggregated, f, ensure_ascii=False, indent=2)

# Print summary
print('\n' + '='*60)
print('AGGREGATED RESULTS:')
print('='*60)
for elem in aggregated:
    print(f"{elem['mark']:<15} {elem['quantity']:<5} {elem['type']:<15} (seen in {elem['tiles_seen']} tiles)")
print('='*60)
print(f'Total elements: {len(aggregated)}')
print(f'Total tiles: {len(tiles)}')
