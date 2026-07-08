import json
import re

with open('/root/.openclaw/workspace/projects/drawings-to-vor/batch_kj5/ocr/ocr_result.json', 'r') as f:
    data = json.load(f)

all_text = ' '.join(' '.join(r.get('text_lines', [])) for r in data)

# Known quantities from VOR
vor_quantities = {
    'Рсм1': 13, 'Рсм2': 1,
    'БФм1': 2, 'БФм2': 1, 'БФм3': 1, 'БФм4': 4, 'БФм5': 1,
    'БФм6': 1, 'БФм7': 2, 'БФм8': 4, 'БФм9': 4, 'БФм10': 2,
    'БФм11': 2, 'БФм12': 2, 'БФм13': 2, 'БФм14': 3, 'БФм15': 1,
    'БФм16': 2, 'БФм17': 2,
    'ФОм1': 1, 'ФОм2': 1, 'ФОм3': 1, 'ФОм4': 1, 'ФОм5': 2, 'ФОм5а': 2,
}

print('=== Поиск известных количеств в OCR ===')
for mark, expected_qty in vor_quantities.items():
    idx = all_text.find(mark)
    if idx >= 0:
        context = all_text[max(0, idx-100):idx+200]
        if str(expected_qty) in context:
            qty_idx = context.find(str(expected_qty))
            mark_idx = context.find(mark)
            distance = abs(qty_idx - mark_idx) if qty_idx >= 0 else -1
            print(f'{mark}: {expected_qty} шт. - найдено (расстояние: {distance} chars)')
        else:
            print(f'{mark}: {expected_qty} шт. - НЕ найдено в контексте')
    else:
        print(f'{mark}: {expected_qty} шт. - марка не найдена')
