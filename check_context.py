import json
import re

with open('/root/.openclaw/workspace/projects/drawings-to-vor/batch_kj5/ocr/ocr_result.json', 'r') as f:
    data = json.load(f)

all_text = ' '.join(' '.join(line for line in r.get('text_lines', [])) for r in data)

# Check context for БФм10
mark = 'БФм10'
idx = all_text.find(mark)
if idx >= 0:
    context = all_text[max(0, idx-150):idx+200]
    print(f'Context for {mark}:')
    print(context)
    print()

# Check for БФм4-9 variants
for i in range(4, 10):
    for variant in [f'БФм{i}', f'БФМ{i}']:
        idx = all_text.find(variant)
        if idx >= 0:
            context = all_text[max(0, idx-50):idx+100]
            print(f'Found {variant}: {context}')

print()
print('=== Searching for БФм4-9 with any case ===')
for i in range(4, 10):
    pattern = re.compile(rf'БФ[мМmM]{i}', re.IGNORECASE)
    matches = list(pattern.finditer(all_text))
    if matches:
        for match in matches[:2]:
            context = all_text[max(0, match.start()-50):match.end()+100]
            print(f'БФм{i}: {context}')
    else:
        print(f'БФм{i}: NOT FOUND')
