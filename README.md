# Drawings → VOR Skill

Извлечение позиций, объёмов и спецификаций из строительных чертежей (PDF, PNG, JPG) с формированием ВОР (Ведомости объёмов работ) в Excel.

## Интеграция с smeta

Этот skill — первый этап пайплайна:

```
[Чертежи] → [drawings-to-vor] → [ВОР.xlsx] → [smeta] → [Смета]
```

## Структура

```
├── src/
│   ├── prepare_drawing.py    # PDF → PNG, определение масштаба
│   ├── validate_vor.py       # Валидация ВОР
│   └── create_vor_template.py # Генератор шаблона ВОР
├── templates/
│   └── ВОР_шаблон.xlsx       # Шаблон Ведомости объёмов работ
├── docs/
│   └── МЕТОДОЛОГИЯ.md        # Подробная методология извлечения
└── SKILL.md                  # Правила и процесс для LLM
```

## Быстрый старт

```bash
# 1. Подготовить чертежи (PDF → PNG)
python3 src/prepare_drawing.py --input чертеж.pdf --output pages/

# 2. Создать шаблон ВОР
python3 src/create_vor_template.py

# 3. Заполнить ВОР (вручную или с помощью LLM анализа)
# → открыть templates/ВОР_шаблон.xlsx, заполнить

# 4. Валидировать ВОР
python3 src/validate_vor.py --vor ВОР.xlsx --drawing_pages pages/

# 5. Передать в smeta
cd /path/to/smeta
cp ВОР.xlsx data/<object>/ВОР.xlsx
make eval SMETA=... VOR=...
```

## Критические правила

1. **Масштаб обязателен** — без него невозможны объёмы
2. **ВОР = единственный источник** для сметы
3. **4-глазый метод** — два прохода: структура, затем детали
4. **«УТОЧНИТЬ» лучше, чем наугад**
5. **Спецификации и чертежи могут расходиться** — фиксировать, не исправлять

## Требования

```bash
pip install -r requirements.txt
```

- `openpyxl` — работа с Excel
- `PyMuPDF` (fitz) — работа с PDF (опционально, но рекомендуется)
- `pdf2image` — альтернативная конвертация PDF (опционально)

## Статус

- Version: 1.0
- Created: 2026-06-30
- Integration: smeta v3.0

---

*Skill для LLM: процессный + automation helpers*