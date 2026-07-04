# drawings-to-vor

Lossless TIFF → PDF → OCR → ВОР pipeline для инженерных чертежей.

## Workflow

```
TIFF (300 DPI, A1) → tiff_to_pdf.py → PDF (lossless)
                   → preprocess.py → PNG tiles (1000×1000, overlap 100px)
                   → tile_ocr.py → JSON/TXT (Alibaba Qwen-VL-OCR)
                   → (manual/extract_tables.py) → CSV/Excel → ВОР
```

## Scripts

### 1. tiff_to_pdf.py — Lossless конвертация
- **Без загрузки в RAM** — потоковая обработка
- Сохраняет DPI, размеры, масштаб A0/A1/A2
- Не пережимает в JPEG

```bash
python scripts/tiff_to_pdf.py КЖ7.tiff output/КЖ7.pdf
python scripts/tiff_to_pdf.py /папка/со/сканами/ output/все_листы.pdf
```

### 2. preprocess.py — Предобработка
- Sharpening + contrast для размытых сканов
- Нарезка на тайлы 1000×1000 с overlap 100px
- Сохраняет координаты в имени файла

```bash
python scripts/preprocess.py КЖ7.tiff --out-dir ./tiles/ --tile-size 1000 --overlap 100
```

### 3. tile_ocr.py — OCR через Alibaba Qwen-VL-OCR
- Base64-кодирование (не загружает никуда файлы)
- Retry logic
- Deduplication перекрывающихся тайлов
- Выход: JSON + TXT

```bash
export DASHSCOPE_API_KEY=sk-xxx
python scripts/tile_ocr.py --tiles-dir ./tiles/ --output ./output/ocr.json
```

## Установка

```bash
pip install -r requirements.txt
```

## Получение API ключа Alibaba

1. Идём на https://www.alibabacloud.com/help/en/model-studio/get-api-key
2. Регистрируемся (trial — бесплатно)
3. Копируем API ключ
4. `export DASHSCOPE_API_KEY=sk-ваш-ключ`

## RAM Usage

| Скрипт | RAM |
|--------|-----|
| tiff_to_pdf.py | ~10 MB (потоковый) |
| preprocess.py | ~50 MB + 1 тайл |
| tile_ocr.py | ~5 MB + base64 буфер |

## Важно

- **НЕ загружайте TIFF на внешние сервисы** — только base64 в Alibaba API
- Тайлы 1000×1000 = оптимум для vision model (не падает)
- A1 (7016×9933) ≈ 80 тайлов на лист

## License

MIT
