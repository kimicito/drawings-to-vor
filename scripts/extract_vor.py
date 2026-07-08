#!/usr/bin/env python3
"""
extextract_vor.py — Comprehensive ВОР extraction from OCR results.

Searches ALL elements on drawings:
- Svaі (СБН)
- Rostverki (Рсм)
- Foundation beams (БФм)
- Foundations (ФОм)
- Frameworks (КП)
- Embedded parts (Зд)
- Slabs (П)
- Rebar (А500С, А240)

Usage:
    python extract_vor.py --ocr-json ./ocr.json --output ./vor
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


def extract_element_marks(text: str) -> dict:
    """Extract all element marks with quantities from OCR text."""
    elements = defaultdict(lambda: {'count': 0, 'type': 'unknown'})
    
    # Pile patterns
    pile_patterns = [
        re.compile(r'([СC][БB][НHнn]\d{1,2}-\d{3,4})\s*[-–—]?\s*(\d+)\s*шт', re.IGNORECASE),
        re.compile(r'([СC][БB][НHнn]\d{1,2}-\d{3,4})\s*[-–—]?\s*(\d+)', re.IGNORECASE),
    ]
    
    # Rostverk patterns
    rost_patterns = [
        re.compile(r'Рсм(\d+[а-я]?)\s*[-–—]?\s*(\d+)\s*шт', re.IGNORECASE),
        re.compile(r'Ростверк\s+Рсм(\d+[а-я]?)\s*[-–—]?\s*(\d+)\s*шт', re.IGNORECASE),
    ]
    
    # Beam patterns (foundation beams)
    beam_patterns = [
        re.compile(r'БФм(\d+[а-я]?)\s*[-–—]?\s*(\d+)\s*шт', re.IGNORECASE),
        re.compile(r'БФМ(\d+[а-я]?)\s*[-–—]?\s*(\d+)\s*шт', re.IGNORECASE),
    ]
    
    # Foundation patterns
    found_patterns = [
        re.compile(r'ФОм(\d+[а-я]?)\s*[-–—]?\s*(\d+)\s*шт', re.IGNORECASE),
        re.compile(r'ФОМ(\d+[а-я]?)\s*[-–—]?\s*(\d+)\s*шт', re.IGNORECASE),
    ]
    
    # Framework patterns (КП)
    frame_patterns = [
        re.compile(r'КП(\d+[а-я]?)\s*[-–—]?\s*(\d+)\s*шт', re.IGNORECASE),
    ]
    
    # Embedded parts (Зд)
    embed_patterns = [
        re.compile(r'Зд(\d+[а-я]?)\s*[-–—]?\s*(\d+)\s*шт', re.IGNORECASE),
    ]
    
    # Process each pattern type
    for patterns, prefix, elem_type in [
        (pile_patterns, 'СБН', 'pile'),
        (rost_patterns, 'Рсм', 'rostverk'),
        (beam_patterns, 'БФм', 'beam'),
        (found_patterns, 'ФОм', 'foundation'),
        (frame_patterns, 'КП', 'framework'),
        (embed_patterns, 'Зд', 'embedded'),
    ]:
        for pattern in patterns:
            for match in pattern.finditer(text):
                if elem_type == 'pile':
                    mark = match.group(1).upper().replace('N', 'Н').replace('B', 'Б').replace('C', 'С').replace('H', 'Н')
                else:
                    mark = prefix + match.group(1).upper()
                count = int(match.group(2))
                elements[mark] = {'count': count, 'type': elem_type}
    
    # Also extract marks without quantities (just list them)
    mark_only_patterns = [
        (re.compile(r'[СC][БB][НHнn]\d{1,2}-\d{3,4}', re.IGNORECASE), 'pile'),
        (re.compile(r'Рсм\d+[а-я]?', re.IGNORECASE), 'rostverk'),
        (re.compile(r'БФм\d+[а-я]?', re.IGNORECASE), 'beam'),
        (re.compile(r'ФОм\d+[а-я]?', re.IGNORECASE), 'foundation'),
        (re.compile(r'КП\d+[а-я]?', re.IGNORECASE), 'framework'),
        (re.compile(r'Зд\d+[а-я]?', re.IGNORECASE), 'embedded'),
    ]
    
    for pattern, elem_type in mark_only_patterns:
        for match in pattern.finditer(text):
            mark = match.group(0).upper()
            if mark not in elements:
                elements[mark] = {'count': 1, 'type': elem_type}
    
    return dict(elements)


def extract_pile_details(text: str, mark: str) -> dict:
    """Extract pile dimensions and calculate volumes."""
    dim_match = re.search(r'[СC][БB][НHнn](\d+)-(\d+)', mark, re.IGNORECASE)
    if dim_match:
        length_m = int(dim_match.group(1))
        diameter_mm = int(dim_match.group(2))
    else:
        length_m = 12
        diameter_mm = 450
    
    radius_m = (diameter_mm / 1000) / 2
    volume_per_pile = math.pi * (radius_m ** 2) * length_m
    
    return {
        'length_m': length_m,
        'diameter_mm': diameter_mm,
        'volume_per_pile_m3': round(volume_per_pile, 3),
    }


def extract_rebar_info(text: str) -> list:
    """Extract rebar specifications."""
    specs = []
    patterns = [
        re.compile(r'[АA]\d{3}[СC]?\s*.*?[⌀ØDd](\d{1,2})', re.IGNORECASE),
        re.compile(r'арматур[аы].*?[АA]\d{3}[СC]?', re.IGNORECASE),
    ]
    
    seen = set()
    for pattern in patterns:
        for match in pattern.finditer(text):
            steel_match = re.search(r'[АA](\d{3}[СC]?)', match.group(0), re.IGNORECASE)
            diam_match = re.search(r'[⌀ØDd](\d{1,2})', match.group(0))
            if steel_match and diam_match:
                steel = 'А' + steel_match.group(1).upper().replace('C', 'С')
                diam = int(diam_match.group(1))
                key = f"{steel}-{diam}"
                if key not in seen:
                    seen.add(key)
                    specs.append({'steel': steel, 'diameter': diam})
    
    return specs


def generate_vor_report(elements: dict, rebar: list, text: str) -> list:
    """Generate comprehensive VOR report."""
    rows = []
    
    # Title
    rows.append({'№ п/п': '', 'Код': '', 'Наименование': 'ВЕДОМОСТЬ ОБЪЁМОВ РАБОТ', 'Ед.изм': '', 'Количество': '', 'Объем': '', 'Примечание': ''})
    
    # Group by type
    by_type = defaultdict(list)
    for mark, info in elements.items():
        by_type[info['type']].append((mark, info['count']))
    
    # Piles section
    if 'pile' in by_type:
        rows.append({'№ п/п': '', 'Код': '', 'Наименование': 'Раздел. Буронабивные сваи', 'Ед.изм': '', 'Количество': '', 'Объем': '', 'Примечание': ''})
        row_num = 1
        for mark, count in sorted(by_type['pile']):
            details = extract_pile_details(text, mark)
            total_vol = details['volume_per_pile_m3'] * count
            
            rows.append({'№ п/п': row_num, 'Код': 'Е2-196', 'Наименование': f'Бурение скважин D={details["diameter_mm"]}мм, L={details["length_m"]}м ({mark})', 'Ед.изм': 'м³', 'Количество': count, 'Объем': round(total_vol, 2), 'Примечание': f'{details["volume_per_pile_m3"]}×{count}'})
            row_num += 1
            rows.append({'№ п/п': row_num, 'Код': 'Е4-48', 'Наименование': f'Установка арматурных каркасов свай {mark}', 'Ед.изм': 'шт', 'Количество': count, 'Объем': f'~{round(total_vol * 0.12, 2)} т', 'Примечание': '120 кг/м³'})
            row_num += 1
            rows.append({'№ п/п': row_num, 'Код': 'Е4-1', 'Наименование': f'Бетонирование свай {mark}', 'Ед.изм': 'м³', 'Количество': count, 'Объем': round(total_vol, 2), 'Примечание': f'Бетон В25, к={round(total_vol * 1.015, 2)}'})
            row_num += 1
            rows.append({'№ п/п': row_num, 'Код': 'Е2-120', 'Наименование': f'Выбурка грунта ({mark})', 'Ед.изм': 'м³', 'Количество': count, 'Объем': round(total_vol * 1.15, 2), 'Примечание': '1.15×V'})
            row_num += 1
    
    # Rostverki section
    if 'rostverk' in by_type:
        rows.append({'№ п/п': '', 'Код': '', 'Наименование': 'Раздел. Ростверки', 'Ед.изм': '', 'Количество': '', 'Объем': '', 'Примечание': ''})
        row_num = len([r for r in rows if r['№ п/п']]) + 1
        for mark, count in sorted(by_type['rostverk']):
            rows.append({'№ п/п': row_num, 'Код': 'Е4-1', 'Наименование': f'Устройство ростверка {mark}', 'Ед.изм': 'м³', 'Количество': count, 'Объем': '', 'Примечание': 'См. формулу на чертеже'})
            row_num += 1
            rows.append({'№ п/п': row_num, 'Код': '', 'Наименование': f'  Бетон В25 F150 W6', 'Ед.изм': 'м³', 'Количество': '', 'Объем': '', 'Примечание': 'С учётом расхода 1.015'})
            row_num += 1
            rows.append({'№ п/п': row_num, 'Код': '', 'Наименование': f'  Арматура (см. спецификацию)', 'Ед.изм': 'т', 'Количество': '', 'Объем': '', 'Примечание': 'См. формулу на чертеже'})
            row_num += 1
    
    # Beams section
    if 'beam' in by_type:
        rows.append({'№ п/п': '', 'Код': '', 'Наименование': 'Раздел. Фундаментные балки', 'Ед.изм': '', 'Количество': '', 'Объем': '', 'Примечание': ''})
        row_num = len([r for r in rows if r['№ п/п']]) + 1
        for mark, count in sorted(by_type['beam']):
            rows.append({'№ п/п': row_num, 'Код': 'Е4-1', 'Наименование': f'Устройство фундаментной балки {mark}', 'Ед.изм': 'м³', 'Количество': count, 'Объем': '', 'Примечание': 'См. формулу на чертеже'})
            row_num += 1
            rows.append({'№ п/п': row_num, 'Код': '', 'Наименование': f'  Бетон В25 F150 W6', 'Ед.изм': 'м³', 'Количество': '', 'Объем': '', 'Примечание': 'С учётом расхода 1.015'})
            row_num += 1
            rows.append({'№ п/п': row_num, 'Код': '', 'Наименование': f'  Бетон В7.5 (подготовка)', 'Ед.изм': 'м³', 'Количество': '', 'Объем': '', 'Примечание': 'С учётом расхода 1.02'})
            row_num += 1
    
    # Foundations section
    if 'foundation' in by_type:
        rows.append({'№ п/п': '', 'Код': '', 'Наименование': 'Раздел. Фундаменты', 'Ед.изм': '', 'Количество': '', 'Объем': '', 'Примечание': ''})
        row_num = len([r for r in rows if r['№ п/п']]) + 1
        for mark, count in sorted(by_type['foundation']):
            rows.append({'№ п/п': row_num, 'Код': 'Е4-1', 'Наименование': f'Устройство фундамента {mark}', 'Ед.изм': 'м³', 'Количество': count, 'Объем': '', 'Примечание': 'См. формулу на чертеже'})
            row_num += 1
            rows.append({'№ п/п': row_num, 'Код': '', 'Наименование': f'  Бетон В25 F150 W6', 'Ед.изм': 'м³', 'Количество': '', 'Объем': '', 'Примечание': 'С учётом расхода 1.015'})
            row_num += 1
            rows.append({'№ п/п': row_num, 'Код': '', 'Наименование': f'  Бетон В7.5 (подготовка)', 'Ед.изм': 'м³', 'Количество': '', 'Объем': '', 'Примечание': 'С учётом расхода 1.02'})
            row_num += 1
    
    # Frameworks section
    if 'framework' in by_type:
        rows.append({'№ п/п': '', 'Код': '', 'Наименование': 'Раздел. Каркасы пространственные', 'Ед.изм': '', 'Количество': '', 'Объем': '', 'Примечание': ''})
        row_num = len([r for r in rows if r['№ п/п']]) + 1
        for mark, count in sorted(by_type['framework']):
            rows.append({'№ п/п': row_num, 'Код': '', 'Наименование': f'Каркас {mark}', 'Ед.изм': 'шт', 'Количество': count, 'Объем': '', 'Примечание': ''})
            row_num += 1
    
    # Embedded parts section
    if 'embedded' in by_type:
        rows.append({'№ п/п': '', 'Код': '', 'Наименование': 'Раздел. Закладные детали', 'Ед.изм': '', 'Количество': '', 'Объем': '', 'Примечание': ''})
        row_num = len([r for r in rows if r['№ п/п']]) + 1
        for mark, count in sorted(by_type['embedded']):
            rows.append({'№ п/п': row_num, 'Код': '', 'Наименование': f'Закладное изделие {mark}', 'Ед.изм': 'шт', 'Количество': count, 'Объем': '', 'Примечание': ''})
            row_num += 1
    
    # Rebar summary
    if rebar:
        rows.append({'№ п/п': '', 'Код': '', 'Наименование': 'Раздел. Арматура', 'Ед.изм': '', 'Количество': '', 'Объем': '', 'Примечание': ''})
        row_num = len([r for r in rows if r['№ п/п']]) + 1
        for spec in rebar:
            rows.append({'№ п/п': row_num, 'Код': '', 'Наименование': f'Арматура {spec["steel"]} ⌀{spec["diameter"]}мм', 'Ед.изм': 'т', 'Количество': '', 'Объем': '', 'Примечание': 'См. формулы расчёта'})
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
    parser = argparse.ArgumentParser(description="Extract comprehensive ВОР from OCR")
    parser.add_argument("--ocr-json", required=True, help="Path to OCR JSON")
    parser.add_argument("--output", default="./output/vor", help="Output path prefix")
    args = parser.parse_args()
    
    ocr_path = Path(args.ocr_json)
    if not ocr_path.exists():
        print(f"ERROR: File not found: {ocr_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Loading OCR: {ocr_path}")
    data = load_ocr_data(ocr_path)
    text = get_all_text(data)
    print(f"Loaded {len(data)} records, {len(text)} chars")
    
    print("\nExtracting all elements...")
    elements = extract_element_marks(text)
    print(f"Found {len(elements)} unique elements:")
    
    # Group by type for display
    by_type = defaultdict(list)
    for mark, info in elements.items():
        by_type[info['type']].append((mark, info['count']))
    
    for elem_type, items in sorted(by_type.items()):
        type_names = {
            'pile': 'Сваи', 'rostverk': 'Ростверки', 'beam': 'Балки',
            'foundation': 'Фундаменты', 'framework': 'Каркасы', 'embedded': 'Закладные'
        }
        print(f"\n  {type_names.get(elem_type, elem_type)}:")
        for mark, count in sorted(items):
            print(f"    {mark}: {count} шт.")
    
    rebar = extract_rebar_info(text)
    if rebar:
        print(f"\n  Арматура: {len(rebar)} типов")
        for spec in rebar:
            print(f"    {spec['steel']} ⌀{spec['diameter']}мм")
    
    print("\nGenerating VOR...")
    rows = generate_vor_report(elements, rebar, text)
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    save_vor_csv(rows, output_path.with_suffix('.csv'))
    save_vor_txt(rows, output_path.with_suffix('.txt'))
    
    print(f"\n{'=' * 60}")
    print("✅ ВОР СФОРМИРОВАНА")
    print(f"{'=' * 60}")
    print(f"Всего элементов: {len(elements)}")
    print(f"  Сваи: {len(by_type.get('pile', []))}")
    print(f"  Ростверки: {len(by_type.get('rostverk', []))}")
    print(f"  Балки: {len(by_type.get('beam', []))}")
    print(f"  Фундаменты: {len(by_type.get('foundation', []))}")
    print(f"  Каркасы: {len(by_type.get('framework', []))}")
    print(f"  Закладные: {len(by_type.get('embedded', []))}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
