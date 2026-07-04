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
cd projects/drawings-to-vor
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Получение API ключа Alibaba

1. Идём на https://www.alibabacloud.com/help/en/model-studio/get-api-key
2. Регистрируемся (trial — бесплатно)
3. **Активируем сервис** в консоли: https://dashscope.console.aliyun.com — пополняем баланс (минимум ¥1 или free trial credits)
4. Копируем API ключ
5. `export DASHSCOPE_API_KEY=sk-ваш-ключ`

## Troubleshooting

### 403 Access Denied
Если получаешь `AccessDenied.Unpurchased` — аккаунт создан, но не активирован:
- Зайди в консоль https://dashscope.console.aliyun.com
- Пополни баланс или активируй trial (обычно дают ¥50–100 бесплатно)
- Без этого **никакие модели** не работают (даже текстовые)

### Альтернативы (если Alibaba не работает)
- **Mistral Free Tier**: https://console.mistral.ai/ — Pixtral (vision, 25 msg/день, без карты)
- **NVIDIA Nemotron OCR v2**: Требует локальной NVIDIA GPU, полностью бесплатно
- **OpenRouter**: https://openrouter.ai/ — агрегирует бесплатные модели (нужен API ключ)

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
