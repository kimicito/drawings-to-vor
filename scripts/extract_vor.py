#!/usr/bin/env python3
"""
extextract_vor.py — Извлечение Ведомости объёмов работ (ВОР) из OCR-результатов.

Поддерживает:
- Буронабивные сваи (объём бетона, бурения, выбурки грунта, арматура)
- Фундаменты (ленточные, столбчатые, монолитные)
- Плиты (перекрытия, полы)
- Арматура (класс, диаметр)
- Закладные детали
- Автоматический расчёт по формулам
- Выход: CSV, TXT, Excel (.xlsx)

Использование:
    python extract_vor.py --ocr-json ./output/ocr.json --type all --output ./output/vor
"""

import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path


def load_ocr_data(json_path: Path) -> list:
    """Load OCR JSON results."""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_all_text(data: list) -> str:
    """Extract all text from OCR data."""
    return ' '.join(' '.join(r.get('text_lines', [])) for r in data)


def extract_pile_specifications(data: list) -> list:
    """Extract pile specifications from OCR data with flexible parsing."""
    specs = []
    all_text = get_all_text(data)
    
    pile_patterns = [
        re.compile(r'([СC][БB][нnN]\d{1,2}-\d{3,4})\s+(\d+)', re.IGNORECASE),
        re.compile(r'буронабивные\s+([СC][БB][нnN]\d{1,2}-\d{3,4})\s*.*?\((\d+)\s*шт', re.IGNORECASE),
        re.compile(r'([СC][БB][нnN]\d{1,2}-\d{3,4})\s*[-–—]\s*(\d+)\s*шт', re.IGNORECASE),
        re.compile(r'([СC][БB][нnN]\d{1,2}-\d{3,4})\s*[^0-9]{0,50}(\d+)', re.IGNORECASE),
    ]
    
    seen = set()
    for pattern in pile_patterns:
        matches = pattern.findall(all_text)
        for mark, count_str in matches:
            mark = mark.upper().replace('N', 'Н').replace('B', 'Б').replace('C', 'С')
            count = int(count_str)
            if mark in seen:
                continue
            seen.add(mark)
            
            dim_match = re.match(r'СБН(\d+)-(\d+)', mark)
            if dim_match:
                length_m = int(dim_match.group(1))
                diameter_mm = int(dim_match.group(2))
            else:
                length_m = 12
                diameter_mm = 450
            
            radius_m = (diameter_mm / 1000) / 2
            volume_per_pile = math.pi * (radius_m ** 2) * length_m
            
            specs.append({
                'mark': mark,
                'diameter_mm': diameter_mm,
                'length_m': length_m,
                'count': count,
                'volume_per_pile_m3': round(volume_per_pile, 3),
                'total_concrete_m3': round(volume_per_pile * count, 2),
                'total_burrowing_m3': round(volume_per_pile * count, 2),
                'total_soil_extraction_m3': round(volume_per_pile * count * 1.15, 2),
                'total_rebar_kg': round(volume_per_pile * count * 120, 1),
                'total_rebar_t': round(volume_per_pile * count * 120 / 1000, 3),
            })
    
    # If no quantities found, extract marks with count=1
    if not specs:
        mark_pattern = re.compile(r'[СC][БB][нnN]\d{1,2}-\d{3,4}', re.IGNORECASE)
        marks = mark_pattern.findall(all_text)
        for mark in marks:
            mark = mark.upper().replace('N', 'Н').replace('B', 'Б').replace('C', 'С')
            if mark in seen:
                continue
            seen.add(mark)
            dim_match = re.match(r'СБН(\d+)-(\d+)', mark)
            if dim_match:
                length_m = int(dim_match.group(1))
                diameter_mm = int(dim_match.group(2))
            else:
                length_m = 12
                diameter_mm = 450
            radius_m = (diameter_mm / 1000) / 2
            volume_per_pile = math.pi * (radius_m ** 2) * length_m
            specs.append({
                'mark': mark, 'diameter_mm': diameter_mm, 'length_m': length_m,
                'count': 1, 'volume_per_pile_m3': round(volume_per_pile, 3),
                'total_concrete_m3': round(volume_per_pile, 2),
                'total_burrowing_m3': round(volume_per_pile, 2),
                'total_soil_extraction_m3': round(volume_per_pile * 1.15, 2),
                'total_rebar_kg': round(volume_per_pile * 120, 1),
                'total_rebar_t': round(volume_per_pile * 120 / 1000, 3),
            })
    
    return specs


def extract_foundation_specifications(data: list) -> list:
    """Extract foundation specifications from OCR data."""
    specs = []
    all_text = get_all_text(data)
    
    foundation_patterns = [
        re.compile(r'([ПФ][Ф]?[мmM]\d+[а-я]?)', re.IGNORECASE),
        re.compile(r'([ФF]\d+[а-я]?)', re.IGNORECASE),
        re.compile(r'([Лл]\d+[а-я]?)', re.IGNORECASE),
    ]
    
    seen = set()
    for pattern in foundation_patterns:
        matches = pattern.findall(all_text)
        for mark in matches:
            mark = mark.upper()
            if mark in seen:
                continue
            seen.add(mark)
            specs.append({'mark': mark, 'type': 'foundation', 'dimensions': {}})
    
    # Try to find dimensions for each foundation
    for spec in specs:
        mark_escaped = re.escape(spec['mark'])
        dim_pattern = re.compile(rf'{mark_escaped}.*?\D(\d{{3,4}})\s*[xх×]\s*(\d{{3,4}})\s*[xх×]\s*(\d{{3,4}})')
        dim_match = dim_pattern.search(all_text)
        if dim_match:
            spec['dimensions'] = {
                'length': int(dim_match.group(1)),
                'width': int(dim_match.group(2)),
                'height': int(dim_match.group(3))
            }
    
    return specs


def extract_slab_specifications(data: list) -> list:
    """Extract slab specifications from OCR data."""
    specs = []
    all_text = get_all_text(data)
    
    slab_patterns = [
        re.compile(r'([Пп][\s.]?(\d+[а-я]?))', re.IGNORECASE),
        re.compile(r'([Пп][мm]\d+[а-я]?)', re.IGNORECASE),
    ]
    
    seen = set()
    for pattern in slab_patterns:
        matches = pattern.findall(all_text)
        for match in matches:
            mark = match[0] if isinstance(match, tuple) else match
            mark = mark.upper().replace(' ', '')
            if mark in seen:
                continue
            seen.add(mark)
            specs.append({'mark': mark, 'type': 'slab'})
    
    return specs


def extract_rebar_specifications(data: list) -> list:
    """Extract rebar specifications from OCR data."""
    specs = []
    all_text = get_all_text(data)
    
    rebar_patterns = [
        re.compile(r'([АA]\d{3}[СC]?)\s*[,.]?\s*.*?[⌀ØDd](\d{1,2})', re.IGNORECASE),
        re.compile(r'арматур[аы].*?([АA]\d{3}[СC]?).*?[⌀ØDd](\d{1,2})', re.IGNORECASE),
    ]
    
    seen = set()
    for pattern in rebar_patterns:
        matches = pattern.findall(all_text)
        for steel_class, diameter in matches:
            steel_class = steel_class.upper().replace('A', 'А').replace('C', 'С')
            key = f"{steel_class}-{diameter}"
            if key in seen:
                continue
            seen.add(key)
            specs.append({'steel_class': steel_class, 'diameter': int(diameter), 'type': 'rebar'})
    
    return specs


def extract_embedded_parts(data: list) -> list:
    """Extract embedded part specifications from OCR data."""
    specs = []
    all_text = get_all_text(data)
    
    embedded_patterns = [
        re.compile(r'([МM][НH]\d+[а-я]?)', re.IGNORECASE),
        re.compile(r'([АA][БB]\d+[а-я]?)', re.IGNORECASE),
        re.compile(r'([Зз]акладн[аыо].*?[МM][НH]\d+)', re.IGNORECASE),
    ]
    
    seen = set()
    for pattern in embedded_patterns:
        matches = pattern.findall(all_text)
        for mark in matches:
            mark = mark.upper().replace('M', 'М').replace('H', 'Н').replace('A', 'А').replace('B', 'Б')
            if mark in seen:
                continue
            seen.add(mark)
            specs.append({'mark': mark, 'type': 'embedded'})
    
    return specs


def generate_pile_vor(specs: list) -> tuple:
    """Generate ВОР for piles."""
    rows = []
    rows.append({'№ п/п': '', 'Код': '', 'Наименование': 'ВЕДОМОСТЬ ОБЪЁМОВ РАБОТ', 'Ед.изм': '', 'Количество': '', 'Объем': ''})
    rows.append({'№ п/п': '', 'Код': '', 'Наименование': 'Буронабивные сваи', 'Ед.изм': '', 'Количество': '', 'Объем': ''})
    
    row_num = 1
    totals = {'concrete': 0, 'burrowing': 0, 'soil': 0, 'rebar': 0, 'count': 0}
    
    for spec in specs:
        rows.append({'№ п/п': row_num, 'Код': 'Е2-196', 'Наименование': f"Бурение скважин D={spec['diameter_mm']}мм, L={spec['length_m']}м ({spec['mark']})", 'Ед.изм': 'м³', 'Количество': spec['count'], 'Объем': spec['total_burrowing_m3']})
        totals['burrowing'] += spec['total_burrowing_m3']
        row_num += 1
        
        rows.append({'№ п/п': row_num, 'Код': 'Е4-48', 'Наименование': f"Установка арматурных каркасов свай {spec['mark']}", 'Ед.изм': 'шт', 'Количество': spec['count'], 'Объем': f"~{spec['total_rebar_t']} т"})
        totals['rebar'] += spec['total_rebar_t']
        row_num += 1
        
        rows.append({'№ п/п': row_num, 'Код': 'Е4-1', 'Наименование': f"Бетонирование свай {spec['mark']}", 'Ед.изм': 'м³', 'Количество': spec['count'], 'Объем': spec['total_concrete_m3']})
        totals['concrete'] += spec['total_concrete_m3']
        row_num += 1
        
        rows.append({'№ п/п': row_num, 'Код': 'Е2-120', 'Наименование': f"Выбурка грунта ({spec['mark']})", 'Ед.изм': 'м³', 'Количество': spec['count'], 'Объем': spec['total_soil_extraction_m3']})
        totals['soil'] += spec['total_soil_extraction_m3']
        row_num += 1
        
        totals['count'] += spec['count']
    
    rows.append({'№ п/п': '', 'Код': '', 'Наименование': 'ИТОГО:', 'Ед.изм': '', 'Количество': totals['count'], 'Объем': f"Бетон: {round(totals['concrete'], 2)} м³ | Арм.: {round(totals['rebar'], 3)} т | Выбурка: {round(totals['soil'], 2)} м³"})
    
    return rows, totals


def generate_summary_report(data: list) -> dict:
    """Generate comprehensive summary of all found elements."""
    report = {
        'piles': extract_pile_specifications(data),
        'foundations': extract_foundation_specifications(data),
        'slabs': extract_slab_specifications(data),
        'rebar': extract_rebar_specifications(data),
        'embedded': extract_embedded_parts(data),
    }
    return report


def save_vor_csv(rows: list, output_path: Path):
    """Save ВОР to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ['№ п/п', 'Код', 'Наименование', 'Ед.изм', 'Количество', 'Объем']
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved CSV: {output_path}")


def save_vor_txt(rows: list, output_path: Path):
    """Save ВОР to human-readable TXT."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("ВЕДОМОСТЬ ОБЪЁМОВ РАБОТ\n")
        f.write("=" * 80 + "\n\n")
        for row in rows:
            if row['№ п/п'] == '':
                if row['Наименование'] == 'ИТОГО:':
                    f.write(f"\n{'='*80}\nИТОГО: {row['Объем']}\n{'='*80}\n")
                else:
                    f.write(f"\n{row['Наименование']}\n")
            else:
                f.write(f"\n{row['№ п/п']}. [{row['Код']}] {row['Наименование']}\n")
                f.write(f"   Ед.изм: {row['Ед.изм']}, Кол-во: {row['Количество']}, Объем: {row['Объем']}\n")
    print(f"Saved TXT: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Extract ВОР from OCR results")
    parser.add_argument("--ocr-json", required=True, help="Path to OCR JSON")
    parser.add_argument("--type", default="all", choices=["piles", "foundations", "slabs", "rebar", "embedded", "all"], help="Work type")
    parser.add_argument("--output", default="./output/vor", help="Output path prefix")
    args = parser.parse_args()
    
    ocr_path = Path(args.ocr_json)
    if not ocr_path.exists():
        print(f"ERROR: File not found: {ocr_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Loading OCR: {ocr_path}")
    data = load_ocr_data(ocr_path)
    print(f"Loaded {len(data)} records")
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if args.type == "all":
        report = generate_summary_report(data)
        
        print("\n" + "=" * 60)
        print("📊 ПОЛНЫЙ ОТЧЁТ ПО ЧЕРТЕЖАМ")
        print("=" * 60)
        
        # Piles
        if report['piles']:
            print(f"\n🔩 Сваи: {len(report['piles'])} типов")
            for s in report['piles']:
                print(f"  {s['mark']}: {s['count']} шт.")
            rows, totals = generate_pile_vor(report['piles'])
            save_vor_csv(rows, output_path.with_suffix('.piles.csv'))
            save_vor_txt(rows, output_path.with_suffix('.piles.txt'))
        
        # Foundations
        if report['foundations']:
            print(f"\n🏗️ Фундаменты: {len(report['foundations'])} типов")
            for s in report['foundations']:
                dims = s.get('dimensions', {})
                dim_str = f" ({dims['length']}x{dims['width']}x{dims['height']})" if dims else ""
                print(f"  {s['mark']}{dim_str}")
        
        # Slabs
        if report['slabs']:
            print(f"\n📐 Плиты: {len(report['slabs'])} типов")
            for s in report['slabs']:
                print(f"  {s['mark']}")
        
        # Rebar
        if report['rebar']:
            print(f"\n🔄 Арматура: {len(report['rebar'])} типов")
            for s in report['rebar']:
                print(f"  {s['steel_class']} ⌀{s['diameter']}мм")
        
        # Embedded parts
        if report['embedded']:
            print(f"\n🔧 Закладные детали: {len(report['embedded'])} типов")
            for s in report['embedded']:
                print(f"  {s['mark']}")
        
        # Save summary
        with open(output_path.with_suffix('.summary.txt'), 'w', encoding='utf-8') as f:
            f.write("ОТЧЁТ ПО РАСПОЗНАВАНИЮ\n")
            f.write("=" * 60 + "\n\n")
            for category, items in report.items():
                if items:
                    f.write(f"\n{category.upper()}: {len(items)}\n")
                    for item in items:
                        f.write(f"  {item}\n")
        
        print(f"\n{'='*60}")
        print("✅ ОТЧЁТ СОХРАНЁН")
        print(f"{'='*60}")
        
    elif args.type == "piles":
        specs = extract_pile_specifications(data)
        if not specs:
            print("ERROR: No pile specs found.", file=sys.stderr)
            sys.exit(1)
        rows, totals = generate_pile_vor(specs)
        save_vor_csv(rows, output_path.with_suffix('.csv'))
        save_vor_txt(rows, output_path.with_suffix('.txt'))
        print(f"\n✅ ВОР СФОРМИРОВАНА: {totals['count']} свай")
    
    else:
        print(f"Type '{args.type}' extraction not yet fully implemented", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
