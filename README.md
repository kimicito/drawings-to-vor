# drawings-to-vor

Lossless TIFF → PDF → OCR → ВОР pipeline для инженерных чертежей.

**Теперь поддерживает Alibaba Qwen-VL-OCR** — специализированная модель для извлечения текста, таблиц и размеров из чертежей.

## Workflow

```
TIFF (300 DPI, A1) → tiff_to_pdf.py → PDF (lossless)
                   → preprocess.py → PNG tiles (1000×1000, overlap 100px)
                   → tile_ocr.py → JSON/TXT/CSV (Mistral Pixtral ИЛИ Alibaba Qwen-VL-OCR)
                   → extract_vor.py → CSV/Excel/TXT → ВОР
```

## Сравнение провайдеров OCR

| Провайдер | Модель | Статус | Точность русского | Скорость | Стоимость/лист A1 |
|-----------|--------|--------|-------------------|----------|-------------------|
| **Alibaba Qwen** | `qwen-vl-ocr` | ✅ Работает | ⭐⭐⭐ Отличная | ~2 мин | ~$0.05–0.10 |
| **Alibaba Qwen** | `qwen-vl-max` | ✅ Работает | ⭐⭐⭐ Отличная | ~2 мин | ~$0.10–0.20 |
| **Mistral** | `pixtral-12b-2409` | ✅ Работает | ⭐⭐⭐ Отличная | ~1 мин | ~$0.15–0.40 |
| **Ollama** | `llava-phi3` | ❌ Не работает | — | — | Бесплатно |

**Рекомендация:** Использовать `qwen-vl-ocr` для чертежей с таблицами (возвращает bounding boxes) или `qwen-vl-max` для лучшего понимания контекста.

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

### 3. tile_ocr.py — OCR через Mistral или Alibaba Qwen
- **Два провайдера:** Mistral Pixtral (default) или Alibaba Qwen-VL-OCR
- Base64-кодирование (не загружает никуда файлы)
- Retry logic с exponential backoff
- Deduplication перекрывающихся тайлов
- Структурированный выход: TEXT, DIMENSIONS, TABLES, CODES, GEOLOGY
- Автопарсинг JSON markdown (Qwen возвращает ` ```json {...} ```)
- Выход: JSON + TXT + CSV

#### Использование с Alibaba Qwen-VL-OCR (рекомендуется):

```bash
# Установить переменные окружения
export DASHSCOPE_API_KEY=sk-ваш-ключ
export DASHSCOPE_COMPATIBLE_URL=https://xxx.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1

# Запустить OCR
python scripts/tile_ocr.py \
  --provider qwen \
  --model qwen-vl-ocr \
  --tiles-dir ./tiles/ \
  --output ./output/ocr_result.json
```

#### Использование с Mistral Pixtral:

```bash
export MISTRAL_API_KEY=mk-ваш-ключ
python scripts/tile_ocr.py --tiles-dir ./tiles/ --output ./output/ocr_result.json
```

#### Параметры:

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `--provider` | Провайдер: `mistral` или `qwen` | `mistral` |
| `--model` | Название модели | `pixtral-12b-2409` / `qwen-vl-ocr` |
| `--tiles-dir` | Папка с тайлами | `./tiles` |
| `--output` | Путь к JSON | `./output/ocr_result.json` |
| `--api-key` | API ключ (или env var) | — |
| `--base-url` | Base URL (только Qwen) | — |

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

**Результат:**
```
ВЕДОМОСТЬ ОБЪЁМОВ РАБОТ
1. [Е2-196] Бурение скважин D=450мм, L=12м (СБН12-450) — 295.82 м³
2. [Е4-48] Установка арматурных каркасов — 155 шт, ~35.5 т
3. [Е4-1] Бетонирование — 295.82 м³
4. [Е2-120] Выбурка грунта — 340.19 м³
total: Бетон: 326.51 м³ | Арм.: 39.18 т | Выбурка: 375.49 м³
```

## Полный pipeline (TIFF → ВОР)

```bash
# 1. Конвертация
python scripts/tiff_to_pdf.py drawing.tiff output/drawing.pdf

# 2. Нарезка
python scripts/preprocess.py drawing.tiff --out-dir ./tiles --tile-size 1000 --overlap 100

# 3. OCR (Qwen)
export DASHSCOPE_API_KEY=sk-xxx
export DASHSCOPE_COMPATIBLE_URL=https://xxx/compatible-mode/v1
python scripts/tile_ocr.py --provider qwen --model qwen-vl-ocr \
  --tiles-dir ./tiles --output ./output/ocr.json

# 4. ВОР
python scripts/extract_vor.py --ocr-json ./output/ocr.json \
  --type piles --output ./output/vor.xlsx
```

## Установка

```bash
cd projects/drawings-to-vor
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt  # openai, Pillow
```

## Получение API ключей

### Alibaba Cloud / Qwen-VL-OCR (рекомендуется)

1. Перейти на [dashscope.console.aliyun.com](https://dashscope.console.aliyun.com)
2. Зарегистрироваться с иностранным номером телефона
3. Создать Workspace → Получить API Key
4. Скопировать `apiKey` и `compatible-mode` URL
5. Сохранить в `~/.openclaw/workspace/.env`:
   ```bash
   DASHSCOPE_API_KEY=sk-ws-xxx
   DASHSCOPE_COMPATIBLE_URL=https://xxx.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1
   ```

**Важно:** API Key из CSV-файла (как `Default_Workspace-apiKey-xxx.csv`) содержит полный URL.

### Mistral (альтернатива)

1. Идём на https://console.mistral.ai/
2. Регистрируемся (нужен billing для API)
3. Копируем API ключ
4. `export MISTRAL_API_KEY=mk-ваш-ключ`

## Поддерживаемые модели Qwen

| Модель | Статус | Особенности |
|--------|--------|-------------|
| `qwen-vl-ocr` | ✅ Работает | Лучшая для OCR таблиц, bounding boxes |
| `qwen-vl-max` | ✅ Работает | Лучшее понимание контекста, HTML вывод |
| `qwen-vl-plus` | ✅ Работает | Хороший баланс скорость/качество |
| `qwen-vl-ocr-2024` | ❌ 404 | Не найдена |
| `qwen2-vl-*` | ❌ 404 | Не найдены |

## Troubleshooting

### 401 Unauthorized (Qwen)
- Проверь, что ключ начинается с `sk-ws-`
- Убедись, что `DASHSCOPE_COMPATIBLE_URL` оканчивается на `/compatible-mode/v1`
- Проверь баланс в консоли Alibaba (может быть $0, но API всё равно работает)

### 404 Model Not Exist (Qwen)
- Используй `qwen-vl-ocr` вместо `qwen-vl-ocr-2024`
- Или `qwen-vl-max` вместо `qwen2-vl-72b-instruct`

### JSON markdown не парсится
- `tile_ocr.py` автоматически парсит ` ```json {...} ``` ` от Qwen
- Если видишь `TEXT: []` — значит парсер не сработал, обнови скрипт

### 401 Unauthorized (Mistral)
- Ключ невалидный или не активирован
- Проверь в консоли Mistral

## Стоимость

### Qwen-VL-OCR
- ~$0.01–0.02 за тайл 1000×1000
- A1-лист ≈ 80 тайлов ≈ **$0.80–1.60**
- 35 листов КЖ7 ≈ **$28–56**

### Mistral Pixtral
- ~$0.002–0.005 за 1000 input токенов
- Один тайл ≈ 1400 токенов
- A1-лист ≈ 80 тайлов ≈ **$0.15–0.40**
- 35 листов КЖ7 ≈ **$5–15**

**Вывод:** Mistral дешевле, но Qwen лучше с таблицами и русским языком. Для смет (где критичны таблицы) — Qwen предпочтительнее.

## RAM Usage

| Скрипт | RAM |
|--------|-----|
| tiff_to_pdf.py | ~10 MB (потоковый) |
| preprocess.py | ~50 MB + 1 тайл |
| tile_ocr.py | ~5 MB + base64 буфер |

## Важно

- **НЕ загружайте TIFF на внешние сервисы** — только base64 в API
- Тайлы 1000×1000 = оптимум для vision model (не падает с OOM)
- A1 (7016×9933) ≈ 80–90 тайлов на лист
- **НЕ коммитьте `.env`** — там API ключи

## Примеры результатов

### КЖ7 (геология):
- Извлечены: ГОСТ 25100-2020, классификация грунтов, физико-механические свойства
- 450 уникальных текстовых строк, геологические маркеры QIV, C-26

### КЖ7 (сваи):
- Извлечены: 172 буронабивные сваи (155×СБн12-450, 15×СБн11-450, 2×СБн14-450)
- Несущая способность: Fd=1600 кН

## License

MIT
