#!/usr/bin/env python3
"""
Подготовка чертежей к анализу:
1. PDF → PNG (постранично)
2. Определение масштаба (поиск в текстовом слое или по подписям)
3. Проверка качества изображений

Использование:
    python3 prepare_drawing.py --input чертеж.pdf --output pages/
"""

import argparse
import sys
import os
from pathlib import Path

try:
    from pdf2image import convert_from_path
    HAS_PDF2IMAGE = True
except ImportError:
    HAS_PDF2IMAGE = False
    print("WARN: pdf2image не установлен. PDF-конвертация недоступна.")
    print("Установка: pip install pdf2image")

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False


def pdf_to_png(pdf_path, output_dir, dpi=200):
    """Конвертирует PDF в PNG страницы."""
    if not HAS_PDF2IMAGE and not HAS_PYMUPDF:
        print("ERROR: Ни pdf2image, ни PyMuPDF не установлены.")
        print("Установите: pip install pdf2image PyMuPDF")
        sys.exit(1)
    
    os.makedirs(output_dir, exist_ok=True)
    
    if HAS_PYMUPDF:
        # Используем PyMuPDF
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=dpi)
            output_path = os.path.join(output_dir, f"page_{i+1:03d}.png")
            pix.save(output_path)
            print(f"  Сохранена: {output_path}")
        doc.close()
    elif HAS_PDF2IMAGE:
        # Используем pdf2image
        images = convert_from_path(pdf_path, dpi=dpi)
        for i, image in enumerate(images):
            output_path = os.path.join(output_dir, f"page_{i+1:03d}.png")
            image.save(output_path, "PNG")
            print(f"  Сохранена: {output_path}")
    
    print(f"\nВсего страниц: {i+1}")
    return i + 1


def detect_scale(pdf_path):
    """Пытается найти масштаб в текстовом слое PDF."""
    if not HAS_PYMUPDF:
        print("WARN: PyMuPDF не установлен — невозможно извлечь текстовый слой.")
        return None
    
    doc = fitz.open(pdf_path)
    scale_keywords = ["масштаб", "масштаб:", "scale", "м=", "1:", "1/"]
    
    for page_num, page in enumerate(doc):
        text = page.get_text()
        lines = text.lower().split('\n')
        
        for line in lines:
            for keyword in scale_keywords:
                if keyword in line:
                    # Ищем паттерн 1:100, 1:50, и т.д.
                    import re
                    match = re.search(r'(1\s*[:/\s]\s*\d+)', line, re.IGNORECASE)
                    if match:
                        scale = match.group(1).replace(' ', '').replace('/', ':')
                        print(f"  Найден масштаб на странице {page_num+1}: {scale}")
                        doc.close()
                        return scale
    
    doc.close()
    print("  Масштаб не найден в текстовом слое.")
    return None


def main():
    parser = argparse.ArgumentParser(description='Подготовка чертежей к анализу')
    parser.add_argument('--input', required=True, help='Входной PDF-файл')
    parser.add_argument('--output', required=True, help='Папка для PNG-страниц')
    parser.add_argument('--dpi', type=int, default=200, help='DPI для конвертации (default: 200)')
    args = parser.parse_args()
    
    print(f"=== Подготовка чертежа ===")
    print(f"Вход:  {args.input}")
    print(f"Выход: {args.output}")
    print(f"DPI:   {args.dpi}")
    print()
    
    # Проверка масштаба
    print("Поиск масштаба...")
    scale = detect_scale(args.input)
    if scale:
        print(f"✅ Масштаб найден: {scale}")
    else:
        print("⚠️  Масштаб НЕ НАЙДЕН. Требуется указать вручную.")
    
    print()
    
    # Конвертация
    print("Конвертация PDF → PNG...")
    num_pages = pdf_to_png(args.input, args.output, args.dpi)
    
    print()
    print(f"✅ Готово: {num_pages} страниц в {args.output}/")
    if not scale:
        print("⚠️  ВАЖНО: Укажите масштаб перед анализом!")
    
    # Сохраняем метаданные
    meta_path = os.path.join(args.output, "metadata.json")
    import json
    metadata = {
        "source": args.input,
        "pages": num_pages,
        "scale_detected": scale,
        "scale_manual": None,
        "dpi": args.dpi,
        "date": __import__('datetime').datetime.now().isoformat()
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"Метаданные: {meta_path}")


if __name__ == "__main__":
    main()
