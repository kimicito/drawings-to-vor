# drawings-to-vor

Lossless TIFF → PDF → OCR → ВОР pipeline для инженерных чертежей.

**Единственный провайдер:** Alibaba Qwen-VL-OCR — специализированная модель для извлечения текста, таблиц и размеров из чертежей.

## Workflow

```
TIFF (300 DPI, A1) → tiff_to_pdf.py → PDF (lossless)
                   → preprocess.py → PNG tiles (1000×1000, overlap 100px)
                   → tile_ocr.py (Qwen-VL-OCR) → JSON/TXT/CSV
                   → extract_vor.py → CSV/Excel/TXT → ВОР
                   → vor_reviewer.py → Report (PASS/FAIL)
```

**Цепочка:** OCR → ВОР → **Reviewer** → Готово / Исправить

## Scripts

### 1. tiff_to_pdf.py — Lossless конвертация
- **Без загрузки в RAM** — потоковая обработка
- Сохраняет DPI, размеры, масштаб A0/A1/A2
- Не пережимает в JPEG

```bash
python scripts/tiff_to_pdf.py КЖ7.tiff output/КЖ7.pdf
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
- Retry с exponential backoff
- Deduplication перекрывающихся тайлов
- Структурированный выход: TEXT, DIMENSIONS, TABLES, CODES, GEOLOGY
- Автопарсинг JSON markdown (Qwen возвращает ` ```json {...} ``` )
- Выход: JSON + TXT + CSV

```bash
export DASHSCOPE_API_KEY=sk-ваш-ключ
export DASHSCOPE_COMPATIBLE_URL=https://xxx.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1

python scripts/tile_ocr.py \
  --model qwen-vl-ocr \
  --tiles-dir ./tiles/ \
  --output ./output/ocr_result.json
```

**Поддерживаемые модели:**
- `qwen-vl-ocr` — лучшая для OCR таблиц, bounding boxes (рекомендуется)
- `qwen-vl-max` — лучшее понимание контекста, HTML вывод
- `qwen-vl-plus` — баланс скорость/качество

### 4. extract_vor.py — Автоматический расчёт ВОР

Извлекает объёмы работ из OCR-результатов и формирует Ведомость объёмов работ (ВОР).

**Поддерживаемые типы работ:**
- **Буронабивные сваи** — бурение, бетонирование, армирование, выбурка грунта
- Автоматический расчёт по формулам (π×r²×h)
- Коэффициент разрыхления грунта (1.15)
- Расчёт арматуры (~120 кг/м³)

**Форматы выхода:** CSV, Excel (.xlsx), TXT

```bash
python scripts/extract_vor.py \
  --ocr-json ./output/piles_qwen.json \
  --type piles \
  --output ./output/vor_piles.xlsx
```

### 5. vor_reviewer.py — Автоматическая проверка ВОР

**P0-проверка без API-вызовов.** Валидирует сгенерированную ВОР на ошибки.

**Проверки:**
- ✅ Все марки из OCR найдены в ВОР (completeness)
- ✅ Нет лишних марок в ВОР (extra marks)
- ✅ Все количества > 0 (zero quantity)
- ✅ Нет дублирующихся марок (duplicates)
- ✅ Количества в разумных пределах (sanity: <1000)

**Выход:** `PASS` (100%) или `FAIL` с детализацией ошибок.

```bash
python scripts/vor_reviewer.py \
  --ocr-json ./output/ocr.json \
  --vor-csv ./output/vor.csv \
  --output ./output/vor_review.json
```

**Пример вывода:**
```
РЕЗУЛЬТАТ ПРОВЕРКИ ВОР: PASS
Оценка: 100.0% (5/5 проверок)
```

---

```bash
# 1. Конвертация
python scripts/tiff_to_pdf.py drawing.tiff output/drawing.pdf

# 2. Нарезка
python scripts/preprocess.py drawing.tiff --out-dir ./tiles --tile-size 1000 --overlap 100

# 3. OCR (Qwen)
export DASHSCOPE_API_KEY=sk-xxx
export DASHSCOPE_COMPATIBLE_URL=https://xxx/compatible-mode/v1
python scripts/tile_ocr.py --model qwen-vl-ocr \
  --tiles-dir ./tiles --output ./output/ocr.json

# 4. ВОР
python scripts/extract_vor.py --ocr-json ./output/ocr.json \
  --type piles --output ./output/vor.xlsx

# 5. Проверка ВОР (P0 — без API)
python scripts/vor_reviewer.py \
  --ocr-json ./output/ocr.json \
  --vor-csv ./output/vor.csv \
  --output ./output/vor_review.json
```

**Упрощённый pipeline одной командой:**
```bash
python scripts/run_pipeline.py \
  --tiff drawing.tiff \
  --output-dir ./output \
  --tile-size 1000 --overlap 100
```

## Установка

```bash
cd projects/drawings-to-vor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt  # Pillow
```

## Получение API ключа Alibaba Cloud

1. Перейти на [dashscope.console.aliyun.com](https://dashscope.console.aliyun.com)
2. Зарегистрироваться с иностранным номером телефона
3. Создать Workspace → Получить API Key
4. Скопировать `apiKey` и `compatible-mode` URL
5. Сохранить в `~/.openclaw/workspace/.env`:
   ```bash
   DASHSCOPE_API_KEY=sk-ws-xxx
   DASHSCOPE_COMPATIBLE_URL=https://xxx.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1
   ```

## Troubleshooting

### 401 Unauthorized
- Проверь, что ключ начинается с `sk-ws-`
- Убедись, что URL оканчивается на `/compatible-mode/v1`

### 404 Model Not Exist
- Используй `qwen-vl-ocr` вместо `qwen-vl-ocr-2024`

### JSON markdown не парсится
- tile_ocr.py автоматически парсит ` ```json {...} ``` ` от Qwen
- Если видишь `TEXT: []` — обнови скрипт

## Стоимость

- ~$0.01–0.02 за тайл 1000×1000
- A1-лист ≈ 80 тайлов ≈ **$0.80–1.60**
- 35 листов КЖ7 ≈ **$28–56**

## RAM Usage

| Скрипт | RAM |
|--------|-----|
| tiff_to_pdf.py | ~10 MB (потоковый) |
| preprocess.py | ~50 MB + 1 тайл |
| tile_ocr.py | ~5 MB + base64 буфер |

## Важно

- **НЕ загружайте TIFF на внешние сервисы** — только base64 в API
- Тайлы 1000×1000 = оптимум (не падает с OOM)
- A1 (7016×9933) ≈ 80–90 тайлов на лист
- **НЕ коммитьте `.env`**

## Примеры результатов

### КЖ7 (геология):
- Извлечены: ГОСТ 25100-2020, классификация грунтов, физико-механические свойства
- 450 уникальных текстовых строк, геологические маркеры QIV, C-26

### КЖ7 (сваи):
- Извлечены: 172 буронабивные сваи (155×СБн12-450, 15×СБн11-450, 2×СБн14-450)
- Несущая способность: Fd=1600 кН
- **ВОР:** Бетон 326.51 м³, Арм. 39.18 т, Выбурка 375.49 м³

## License

MIT
