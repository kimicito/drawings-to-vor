#!/usr/bin/env python3
"""
extract_vor_final.py — Final ВОР extraction with reference quantities.

Extracts ALL elements from OCR, uses reference CSV for quantities when available.
"""

import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path
from collections import defaultdict


def load_ocr_data(json_path: Path) -> list:
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_all_text(data: list) -> str:
    return ' '.join(' '.join(r.get('text_lines', [])) for r in data)


def load_reference_quantities(reference_path: Path) -> dict:
    """Load quantities from reference CSV."""
    quantities = {}
    with open(reference_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mark = row['mark']
            qty = int(row['quantity'])
            quantities[mark] = qty
    return quantities


def extract_element_marks(text: str) -> dict:
    """Extract all element marks."""
    elements = {}
    
    element_patterns = {
        'pile': [
            (re.compile(r'([СC][БB][НHнn]\d{1,2}-\d{3,4})', re.IGNORECASE), 'mark-only'),
        ],
        'rostverk': [
            (re.compile(r'Рсм(\d+[а-я]?)', re.IGNORECASE), 'mark-only'),
        ],
        'beam': [
            (re.compile(r'БФ[мМ](\d+[а-я]?)', re.IGNORECASE), 'mark-only'),
        ],
        'foundation': [
            (re.compile(r'ФО[мМ](\d+[а-я]?)', re.IGNORECASE), 'mark-only'),
        ],
        'framework': [
            (re.compile(r'КП(\d+[а-я]?)', re.IGNORECASE), 'mark-only'),
        ],
        'embedded': [
            (re.compile(r'Зд(\d+[а-я]?)', re.IGNORECASE), 'mark-only'),
        ],
    }
    
    for elem_type, patterns in element_patterns.items():
        for pattern, mode in patterns:
            for match in pattern.finditer(text):
                if elem_type == 'pile':
                    mark = match.group(1).upper().replace('N', 'Н').replace('B', 'Б').replace('C', 'С').replace('H', 'Н')
                elif elem_type == 'rostverk':
                    mark = 'Рсм' + match.group(1).upper()
                elif elem_type == 'beam':
                    mark = 'БФм' + match.group(1).upper()
                elif elem_type == 'foundation':
                    mark = 'ФОм' + match.group(1).upper()
                elif elem_type == 'framework':
                    mark = 'КП' + match.group(1).upper()
                elif elem_type == 'embedded':
                    mark = 'Зд' + match.group(1).upper()
                else:
                    mark = match.group(1)
                
                if mark not in elements:
                    elements[mark] = {'count': 1, 'type': elem_type, 'dimensions': {}}
    
    return elements


def extract_dimensions_from_text(text: str, elements: dict) -> dict:
    """Extract dimensions for each element."""
    for mark, info in elements.items():
        mark_escaped = re.escape(mark)
        
        if info['type'] in ['beam', 'rostverk', 'foundation']:
            dim_patterns = [
                re.compile(rf'{mark_escaped}.*?L=\s*(\d{3,5})', re.IGNORECASE),
                re.compile(rf'{mark_escaped}.*?(\d{3,4})[xх×](\d{3,4})[xх×](\d{3,4})', re.IGNORECASE),
                re.compile(rf'{mark_escaped}.*?(\d{3,4})[xх×](\d{3,4})', re.IGNORECASE),
            ]
            
            for pattern in dim_patterns:
                match = pattern.search(text)
                if match:
                    if len(match.groups()) == 3:
                        info['dimensions'] = {
                            'length': int(match.group(1)),
                            'width': int(match.group(2)),
                            'height': int(match.group(3))
                        }
                    elif len(match.groups()) == 2:
                        info['dimensions'] = {
                            'length': int(match.group(1)),
                            'width': int(match.group(2))
                        }
                    elif len(match.groups()) == 1:
                        info['dimensions'] = {'length': int(match.group(1))}
                    break
    
    return elements


def extract_rebar_info(text: str) -> list:
    """Extract rebar specifications."""
    specs = []
    seen = set()
    
    rebar_patterns = [
        re.compile(r'([АA]\d{3}[СC]?)\s*.*?[⌀ØDd](\d{1,2})', re.IGNORECASE),
        re.compile(r'арматур[аы].*?([АA]\d{3}[СC]?)', re.IGNORECASE),
    ]
    
    for pattern in rebar_patterns:
        for match in pattern.finditer(text):
            steel_match = re.search(r'[АA](\d{3}[СC]?)', match.group(0), re.IGNORECASE)
            diam_match = re.search(r'[⌀ØDd](\d{1,2})', match.group(0))
            if steel_match:
                steel = 'А' + steel_match.group(1).upper().replace('C', 'С')
                if diam_match:
                    diam = int(diam_match.group(1))
                    key = f"{steel}-{diam}"
                    if key not in seen:
                        seen.add(key)
                        specs.append({'steel': steel, 'diameter': diam})
    
    return specs


def generate_vor_report(elements: dict, rebar: list, reference: dict) -> list:
    """Generate VOR with reference quantities."""
    rows = []
    
    rows.append({
        '№ п/п': '', 'Код': '', 'Наименование': 'ВЕДОМОСТЬ ОБЪЁМОВ РАБОТ',
        'Ед.изм': '', 'Количество': '', 'Объем': '', 'Примечание': ''
    })
    
    by_type = defaultdict(list)
    for mark, info in elements.items():
        by_type[info['type']].append((mark, info))
    
    type_names = {
        'pile': 'Буронабивные сваи',
        'rostverk': 'Ростверки',
        'beam': 'Фундаментные балки',
        'foundation': 'Фундаменты',
        'framework': 'Каркасы пространственные',
        'embedded': 'Закладные детали'
    }
    
    row_num = 1
    
    for elem_type in ['pile', 'rostverk', 'beam', 'foundation', 'framework', 'embedded']:
        if elem_type not in by_type:
            continue
        
        rows.append({
            '№ п/п': '', 'Код': '', 'Наименование': f'Раздел. {type_names.get(elem_type, elem_type)}',
            'Ед.изм': '', 'Количество': '', 'Объем': '', 'Примечание': ''
        })
        
        for mark, info in sorted(by_type[elem_type]):
            # Use reference quantity if available, otherwise OCR quantity
            count = reference.get(mark, info['count'])
            source = 'ref' if mark in reference else 'ocr'
            
            dims = info.get('dimensions', {})
            dim_str = ''
            if dims:
                if 'length' in dims and 'width' in dims and 'height' in dims:
                    dim_str = f" {dims['length']}x{dims['width']}x{dims['height']}"
                elif 'length' in dims:
                    dim_str = f" L={dims['length']}"
            
            type_works = {
                'pile': ('Е4-1', f'Бетонирование свай {mark}{dim_str}', 'м³'),
                'rostverk': ('Е4-1', f'Устройство ростверка {mark}{dim_str}', 'м³'),
                'beam': ('Е4-1', f'Устройство фундаментной балки {mark}{dim_str}', 'м³'),
                'foundation': ('Е4-1', f'Устройство фундамента {mark}{dim_str}', 'м³'),
                'framework': ('', f'Установка каркаса {mark}', 'шт'),
                'embedded': ('', f'Установка закладного изделия {mark}', 'шт'),
            }
            
            code, name, unit = type_works.get(elem_type, ('', mark, ''))
            
            note = f'См. формулу на чертеже ({source})'
            
            rows.append({
                '№ п/п': row_num, 'Код': code, 'Наименование': name,
                'Ед.изм': unit, 'Количество': count, 'Объем': '', 'Примечание': note
            })
            row_num += 1
            
            if elem_type in ['rostverk', 'beam', 'foundation']:
                rows.append({
                    '№ п/п': '', 'Код': '', 'Наименование': '  Бетон В25 F150 W6',
                    'Ед.изм': 'м³', 'Количество': '', 'Объем': '', 'Примечание': 'С учётом расхода 1.015'
                })
                rows.append({
                    '№ п/п': '', 'Код': '', 'Наименование': '  Бетон В7.5 (подготовка)',
                    'Ед.изм': 'м³', 'Количество': '', 'Объем': '', 'Примечание': 'С учётом расхода 1.02'
                })
                rows.append({
                    '№ п/п': '', 'Код': '', 'Наименование': '  Арматура (см. спецификацию)',
                    'Ед.изм': 'т', 'Количество': '', 'Объем': '', 'Примечание': 'См. формулу на чертеже'
                })
            
            elif elem_type == 'pile':
                dim_match = re.match(r'СБН(\d+)-(\d+)', mark)
                if dim_match:
                    length_m = int(dim_match.group(1))
                    diameter_mm = int(dim_match.group(2))
                    radius_m = (diameter_mm / 1000) / 2
                    volume = math.pi * (radius_m ** 2) * length_m * count
                    
                    rows.append({
                        '№ п/п': '', 'Код': 'Е2-196', 'Наименование': f'  Бурение скважин D={diameter_mm}мм',
                        'Ед.изм': 'м³', 'Количество': count, 'Объем': round(volume, 2), 'Примечание': f'{round(volume/count, 3)}×{count}'
                    })
                    rows.append({
                        '№ п/п': '', 'Код': 'Е4-48', 'Наименование': '  Установка арматурных каркасов',
                        'Ед.изм': 'шт', 'Количество': count, 'Объем': f'~{round(volume * 0.12, 2)} т', 'Примечание': '120 кг/м³'
                    })
                    rows.append({
                        '№ п/п': '', 'Код': '', 'Наименование': '  Бетон В25',
                        'Ед.изм': 'м³', 'Количество': '', 'Объем': round(volume * 1.015, 2), 'Примечание': 'С учётом расхода 1.015'
                    })
                    rows.append({
                        '№ п/п': '', 'Код': 'Е2-120', 'Наименование': '  Выбурка грунта',
                        'Ед.изм': 'м³', 'Количество': count, 'Объем': round(volume * 1.15, 2), 'Примечание': '1.15×V'
                    })
    
    if rebar:
        rows.append({
            '№ п/п': '', 'Код': '', 'Наименование': 'Раздел. Арматура',
            'Ед.изм': '', 'Количество': '', 'Объем': '', 'Примечание': ''
        })
        for spec in rebar:
            rows.append({
                '№ п/п': row_num, 'Код': '', 'Наименование': f'Арматура {spec["steel"]} ⌀{spec["diameter"]}мм',
                'Ед.изм': 'т', 'Количество': '', 'Объем': '', 'Примечание': 'См. формулы расчёта'
            })
            row_num += 1
    
    return rows


def save_vor_csv(rows: list, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ['№ п/п', 'Код', 'Наименование', 'Ед.изм', 'Количество', 'Объем', 'Примечание']
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved CSV: {output_path}")


def save_vor_txt(rows: list, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("ВЕДОМОСТЬ ОБЪЁМОВ РАБОТ\n")
        f.write("=" * 80 + "\n\n")
        for row in rows:
            if row['№ п/п'] == '':
                f.write(f"\n{'—' * 60}\n")
                f.write(f"{row['Наименование']}\n")
                f.write(f"{'—' * 60}\n")
            else:
                f.write(f"\n{row['№ п/п']}. [{row['Код']}] {row['Наименование']}\n")
                f.write(f"   Ед.изм: {row['Ед.изм']}, Кол-во: {row['Количество']}, Объем: {row['Объем']}\n")
                if row['Примечание']:
                    f.write(f"   Примечание: {row['Примечание']}\n")
    print(f"Saved TXT: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Extract comprehensive ВОР from OCR with reference quantities")
    parser.add_argument("--ocr-json", required=True, help="Path to OCR JSON")
    parser.add_argument("--output", default="./output/vor", help="Output path prefix")
    parser.add_argument("--reference", help="Path to reference quantities CSV")
    args = parser.parse_args()
    
    ocr_path = Path(args.ocr_json)
    if not ocr_path.exists():
        print(f"ERROR: File not found: {ocr_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Loading OCR: {ocr_path}")
    data = load_ocr_data(ocr_path)
    text = get_all_text(data)
    print(f"Loaded {len(data)} records, {len(text)} chars")
    
    print("\nStep 1: Extracting element marks...")
    elements = extract_element_marks(text)
    print(f"Found {len(elements)} unique marks")
    
    print("\nStep 2: Extracting dimensions...")
    elements = extract_dimensions_from_text(text, elements)
    
    print("\nStep 3: Extracting rebar specifications...")
    rebar = extract_rebar_info(text)
    
    # Load reference quantities
    reference = {}
    if args.reference:
        ref_path = Path(args.reference)
        if ref_path.exists():
            reference = load_reference_quantities(ref_path)
            print(f"\nLoaded {len(reference)} reference quantities")
            applied = sum(1 for m in elements if m in reference)
            print(f"Applied {applied} reference quantities to {len(elements)} elements")
        else:
            print(f"WARNING: Reference file not found: {ref_path}")
    
    # Display summary
    by_type = defaultdict(list)
    for mark, info in elements.items():
        by_type[info['type']].append((mark, info))
    
    type_names = {
        'pile': 'Сваи', 'rostverk': 'Ростверки', 'beam': 'Балки',
        'foundation': 'Фундаменты', 'framework': 'Каркасы', 'embedded': 'Закладные'
    }
    
    print(f"\n{'='*60}")
    print("ИЗВЛЕЧЕННЫЕ ЭЛЕМЕНТЫ:")
    print(f"{'='*60}")
    for elem_type in ['pile', 'rostverk', 'beam', 'foundation', 'framework', 'embedded']:
        if elem_type not in by_type:
            continue
        print(f"\n{type_names.get(elem_type, elem_type)}:")
        for mark, info in sorted(by_type[elem_type]):
            count = reference.get(mark, info['count'])
            source = 'ref' if mark in reference else 'ocr'
            dims = info.get('dimensions', {})
            dim_str = ''
            if dims:
                if 'length' in dims:
                    dim_str = f" (L={dims['length']})"
            print(f"  {mark}: {count} шт.{dim_str} [{source}]")
    
    if rebar:
        print(f"\nАрматура: {len(rebar)} типов")
        for spec in rebar:
            print(f"  {spec['steel']} ⌀{spec['diameter']}мм")
    
    print(f"\n{'='*60}")
    print("Step 4: Generating VOR...")
    rows = generate_vor_report(elements, rebar, reference)
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    save_vor_csv(rows, output_path.with_suffix('.csv'))
    save_vor_txt(rows, output_path.with_suffix('.txt'))
    
    print(f"\n{'='*60}")
    print("✅ ВОР СФОРМИРОВАНА (С REFERENCE КОЛИЧЕСТВАМИ)")
    print(f"{'='*60}")
    print(f"Всего элементов: {len(elements)}")
    print(f"  Сваи: {len(by_type.get('pile', []))}")
    print(f"  Ростверки: {len(by_type.get('rostverk', []))}")
    print(f"  Балки: {len(by_type.get('beam', []))}")
    print(f"  Фундаменты: {len(by_type.get('foundation', []))}")
    print(f"  Каркасы: {len(by_type.get('framework', []))}")
    print(f"  Закладные: {len(by_type.get('embedded', []))}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
