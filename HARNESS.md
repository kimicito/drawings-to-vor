# HARNESS.md — Проект: drawings-to-vor

## Назначение

Автоматическая обработка инженерных чертежей (TIFF) → OCR → извлечение спецификаций свай → ВОР.

## Архитектура

```
[TIFF чертёж] → [Нарезка на тайлы] → [OCR (Qwen-VL)] → [Извлечение данных] → [ВОР]
```

## Компоненты

| Компонент | Файл | Ответственность |
|-----------|------|-----------------|
| Нарезка | `scripts/preprocess.py` | TIFF → тайлы 1000×1000 |
| OCR | `scripts/tile_ocr.py` | Тайлы → JSON (Alibaba Qwen-VL) |
| Извлечение | `scripts/extract_vor.py` | JSON → таблица свай |
| Агрегация | `scripts/combine_vor.py` | Объединение нескольких ВОР |

## Параметры

- **Tile size:** 1000×1000 (overlap 100)
- **OCR model:** `qwen-vl-ocr`
- **API:** Alibaba DashScope
- **Результат:** `output/VOR_TOTAL.txt`

## Запуск

```bash
cd projects/drawings-to-vor
source venv/bin/activate

# Полный pipeline
python3 scripts/preprocess.py samples/*.tiff
python3 scripts/tile_ocr.py tiles/
python3 scripts/extract_vor.py ocr_output/
python3 scripts/combine_vor.py output/
```

## Файлы проекта

```
drawings-to-vor/
├── scripts/          # Python-скрипты
├── samples/          # Исходные TIFF (не в git)
├── tiles/            # Нарезанные тайлы (не в git)
├── ocr_output/       # Результаты OCR (в git)
├── output/           # Итоговые ВОР (в git)
├── venv/             # Виртуальное окружение (не в git)
└── HARNESS.md        # Этот файл
```

## Ограничения

- TIFF только в оттенках серого
- Минимальный размер тайла: 500×500
- API rate limits: смотреть в консоли Alibaba

## Чеклист перед запуском

- [ ] TIFF файлы в `samples/`
- [ ] `.env` с API ключом
- [ ] `venv` активирован
- [ ] Достаточно места на диске (тайлы ~10× размер TIFF)
