#!/usr/bin/env python3
"""
vor_reviewer.py — Automated Reviewer for ВОР (Ведомость Объёмов Работ).

Validates generated VOR against OCR source data without external API calls.
Checks: completeness, duplicates, logical consistency, missing elements.

Usage:
    python vor_reviewer.py --ocr-json ./ocr.json --vor-csv ./vor.csv --output ./review.json
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from collections import defaultdict


def normalize_mark(mark: str) -> str:
    """Normalize mark to canonical form (e.g., БФМ1 → БФм1, БФм16А → БФм16а)."""
    mark = mark.strip()
    # Convert to lowercase for consistent processing, then capitalize prefix
    mark_lower = mark.lower()
    prefixes = {
        'рсм': 'Рсм', 'бфм': 'БФм', 'фом': 'ФОм', 'кп': 'КП', 'зд': 'Зд', 'сбн': 'СБН',
    }
    for prefix_lower, prefix_canonical in prefixes.items():
        if mark_lower.startswith(prefix_lower):
            rest = mark_lower[len(prefix_lower):]
            return prefix_canonical + rest
    return mark


def load_ocr_marks(ocr_path: Path) -> set:
    """Extract all unique element marks from OCR JSON."""
    with open(ocr_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    all_text = ' '.join(' '.join(r.get('text_lines', [])) for r in data)
    
    marks = set()
    patterns = [
        (re.compile(r'Рсм(\d+[а-я]?)', re.IGNORECASE), lambda m: 'Рсм' + m.group(1)),
        (re.compile(r'БФ[мМ](\d+[а-я]?)', re.IGNORECASE), lambda m: 'БФм' + m.group(1)),
        (re.compile(r'ФО[мМ](\d+[а-я]?)', re.IGNORECASE), lambda m: 'ФОм' + m.group(1)),
        (re.compile(r'КП(\d+[а-я]?)', re.IGNORECASE), lambda m: 'КП' + m.group(1)),
        (re.compile(r'Зд(\d+[а-я]?)', re.IGNORECASE), lambda m: 'Зд' + m.group(1)),
        (re.compile(r'([СC][БB][НHнn]\d{1,2}-\d{3,4})', re.IGNORECASE), 
         lambda m: m.group(1).upper().replace('N', 'Н').replace('B', 'Б').replace('C', 'С').replace('H', 'Н')),
    ]
    
    for pattern, formatter in patterns:
        for match in pattern.finditer(all_text):
            marks.add(normalize_mark(formatter(match)))
    
    return marks


def load_vor_marks(vor_path: Path) -> dict:
    """Extract marks and quantities from VOR CSV."""
    marks = {}
    with open(vor_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            name = row.get('Наименование', '')
            qty_str = row.get('Количество', '')
            
            # Extract mark from name
            mark_match = re.search(r'(Рсм\d+[а-я]?|Б[Фф][мМ]\d+[а-я]?|Ф[Оо][мМ]\d+[а-я]?|К[Пп]\d+[а-я]?|З[Дд]\d+[а-я]?|С[Бб][Нн]\d+-\d+)', 
                                   name, re.IGNORECASE)
            if mark_match:
                mark = normalize_mark(mark_match.group(1))
                if mark not in marks:
                    marks[mark] = {'quantity': 0, 'rows': []}
                try:
                    qty = int(qty_str) if qty_str else 0
                except ValueError:
                    qty = 0
                marks[mark]['quantity'] = qty
                marks[mark]['rows'].append(row)
    
    return marks


def review_vor(ocr_marks: set, vor_marks: dict) -> dict:
    """Run all validation checks."""
    issues = []
    warnings = []
    passed = []
    
    # Check 1: All OCR marks present in VOR
    missing_in_vor = ocr_marks - set(vor_marks.keys())
    if missing_in_vor:
        issues.append({
            'severity': 'ERROR',
            'check': 'completeness',
            'message': f'Марки из OCR отсутствуют в ВОР: {sorted(missing_in_vor)}',
            'count': len(missing_in_vor)
        })
    else:
        passed.append('Все марки из OCR найдены в ВОР')
    
    # Check 2: No extra marks in VOR (not in OCR)
    extra_in_vor = set(vor_marks.keys()) - ocr_marks
    if extra_in_vor:
        warnings.append({
            'severity': 'WARNING',
            'check': 'extra_marks',
            'message': f'Марки в ВОР не найдены в OCR: {sorted(extra_in_vor)}',
            'count': len(extra_in_vor)
        })
    else:
        passed.append('Все марки в ВОР подтверждены OCR')
    
    # Check 3: All quantities > 0
    zero_qty = [m for m, info in vor_marks.items() if info['quantity'] <= 0]
    if zero_qty:
        issues.append({
            'severity': 'ERROR',
            'check': 'zero_quantity',
            'message': f'Нулевое/отсутствующее количество: {sorted(zero_qty)}',
            'count': len(zero_qty)
        })
    else:
        passed.append('Все количества > 0')
    
    # Check 4: No duplicate marks in VOR
    duplicates = []
    for mark, info in vor_marks.items():
        if len(info['rows']) > 1:
            duplicates.append(f'{mark} ({len(info["rows"])} раз)')
    if duplicates:
        warnings.append({
            'severity': 'WARNING',
            'check': 'duplicates',
            'message': f'Дублирующиеся марки в ВОР: {duplicates}',
            'count': len(duplicates)
        })
    else:
        passed.append('Дублей марок нет')
    
    # Check 5: Reasonable quantities (sanity checks)
    unreasonable = []
    for mark, info in vor_marks.items():
        qty = info['quantity']
        if qty > 1000:
            unreasonable.append(f'{mark}: {qty} (слишком много?)')
        elif qty > 100 and mark.startswith('Рсм'):
            unreasonable.append(f'{mark}: {qty} (ростверков >100?)')
    if unreasonable:
        warnings.append({
            'severity': 'WARNING',
            'check': 'sanity',
            'message': f'Подозрительные количества: {unreasonable}',
            'count': len(unreasonable)
        })
    else:
        passed.append('Количества в разумных пределах')
    
    # Summary
    total_checks = len(passed) + len(warnings) + len(issues)
    score = len(passed) / total_checks if total_checks > 0 else 0
    
    return {
        'status': 'PASS' if not issues else 'FAIL',
        'score': round(score * 100, 1),
        'ocr_marks_found': len(ocr_marks),
        'vor_marks_found': len(vor_marks),
        'missing_marks': sorted(missing_in_vor) if missing_in_vor else [],
        'extra_marks': sorted(extra_in_vor) if extra_in_vor else [],
        'passed': passed,
        'warnings': warnings,
        'issues': issues,
    }


def print_review(review: dict):
    """Pretty-print review results."""
    print('=' * 70)
    print(f'РЕЗУЛЬТАТ ПРОВЕРКИ ВОР: {review["status"]}')
    print(f'Оценка: {review["score"]}% ({len(review["passed"])}/{len(review["passed"])+len(review["warnings"])+len(review["issues"])} проверок)')
    print('=' * 70)
    
    print(f'\nМарок в OCR: {review["ocr_marks_found"]}')
    print(f'Марок в ВОР: {review["vor_marks_found"]}')
    
    if review['missing_marks']:
        print(f'\n❌ ПРОПУЩЕНЫ в ВОР ({len(review["missing_marks"])}):')
        for m in review['missing_marks']:
            print(f'   • {m}')
    
    if review['extra_marks']:
        print(f'\n⚠️  ДОПОЛНИТЕЛЬНЫ в ВОР ({len(review["extra_marks"])}):')
        for m in review['extra_marks']:
            print(f'   • {m}')
    
    if review['issues']:
        print(f'\n❌ ОШИБКИ ({len(review["issues"])}):')
        for issue in review['issues']:
            print(f'   [{issue["check"]}] {issue["message"]}')
    
    if review['warnings']:
        print(f'\n⚠️  ПРЕДУПРЕЖДЕНИЯ ({len(review["warnings"])}):')
        for warn in review['warnings']:
            print(f'   [{warn["check"]}] {warn["message"]}')
    
    if review['passed']:
        print(f'\n✅ ПРОЙДЕНЫ ({len(review["passed"])}):')
        for p in review['passed']:
            print(f'   • {p}')
    
    print('=' * 70)


def main():
    parser = argparse.ArgumentParser(description='Automated Reviewer for ВОР')
    parser.add_argument('--ocr-json', required=True, help='Path to OCR JSON')
    parser.add_argument('--vor-csv', required=True, help='Path to VOR CSV')
    parser.add_argument('--output', help='Path to save review JSON')
    args = parser.parse_args()
    
    ocr_path = Path(args.ocr_json)
    vor_path = Path(args.vor_csv)
    
    if not ocr_path.exists():
        print(f'ERROR: OCR not found: {ocr_path}', file=sys.stderr)
        sys.exit(1)
    if not vor_path.exists():
        print(f'ERROR: VOR not found: {vor_path}', file=sys.stderr)
        sys.exit(1)
    
    print('Loading OCR marks...')
    ocr_marks = load_ocr_marks(ocr_path)
    print(f'Found {len(ocr_marks)} unique marks in OCR')
    
    print('Loading VOR marks...')
    vor_marks = load_vor_marks(vor_path)
    print(f'Found {len(vor_marks)} unique marks in VOR')
    
    print('\nRunning review...')
    review = review_vor(ocr_marks, vor_marks)
    
    print_review(review)
    
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(review, f, ensure_ascii=False, indent=2)
        print(f'\nReview saved to: {out_path}')
    
    # Exit with error code if issues found
    sys.exit(0 if review['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
