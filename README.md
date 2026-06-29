# Drawings → VOR → Smeta Pipeline

## Архитектура пайплайна

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Чертежи PDF   │ ──▶ │  drawings-to-vor │ ──▶ │     smeta       │
│  (КЖ, КР, АР)   │     │  (ВОР.xlsx)     │     │  (Смета.xlsx)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
   PDF/PNG/JPG            Excel с объёмами        ЛСР с ценами
   Масштаб, спецификации  Позиции, ед.изм,        ФЕР-2020, БИМ
                          количества              НР, СП, ФССЦ
```

**Связь:** `drawings-to-vor` — это **Stage 1** пайплайна. Его выход (`ВОР.xlsx`) — это **единственный вход** для `smeta` (Stage 2).

---

## Быстрый старт (полный пайплайн)

```bash
# === STAGE 1: Чертежи → ВОР ===
cd skills/drawings-to-vor

# 1. Подготовить чертежи
python3 src/prepare_drawing.py --input чертеж.pdf --output pages/

# 2. Создать шаблон ВОР
python3 src/create_vor_template.py

# 3. Заполнить ВОР (вручную или с LLM)
# → открыть templates/ВОР_шаблон.xlsx, заполнить

# 4. Валидировать ВОР
python3 src/validate_vor.py --vor ВОР.xlsx --drawing_pages pages/

# === STAGE 2: ВОР → Смета ===
cd ../smeta

# 5. Скопировать ВОР в data проекта
cp ../drawings-to-vor/ВОР.xlsx data/<object>/ВОР.xlsx

# 6. Составить смету
# → использовать SKILL.md smeta (БИМ-методика, ФЕР-2020)

# 7. Проверить
python3 eval_smeta.py --smeta смета.xlsx --vor data/<object>/ВОР.xlsx
```

---

## Структура репозитория

```
drawings-to-vor/
├── README.md                 # Этот файл — входная точка
├── SKILL.md                  # Полные правила для LLM
├── knowledge_base.md         # Уроки и коэффициенты (shared)
├── Makefile                  # Автоматизация
├── requirements.txt          # Зависимости Python
│
├── src/                      # Исходный код
│   ├── prepare_drawing.py    # PDF → PNG, определение масштаба
│   ├── validate_vor.py       # Валидация ВОР
│   ├── create_vor_template.py # Генератор шаблона ВОР
│   └── ocr_pipeline.py       # OCR: 3 уровня fallback (NEW)
│
├── templates/
│   └── ВОР_шаблон.xlsx       # Шаблон Ведомости объёмов работ
│
└── docs/
    └── МЕТОДОЛОГИЯ.md        # Подробная методология извлечения
```

---

## Интеграция со smeta

| Что передаётся | Куда | Формат |
|----------------|------|--------|
| ВОР.xlsx | `smeta/data/<object>/ВОР.xlsx` | Excel (позиции, ед.изм, количества) |
| knowledge_base.md | `smeta/knowledge_base.md` | Markdown (коэффициенты, правила) |

**Контракт:** ВОР — единственный источник объёмов для сметы. Ничего не добавлять в смету, чего нет в ВОР.

---

## Версии и зависимости

| Компонент | Версия | Репозиторий |
|-----------|--------|-------------|
| drawings-to-vor | 1.2 | `github.com/kimicito/drawings-to-vor` |
| smeta | 3.0+ | `github.com/kimicito/openclaw-workspace/skills/smeta` |

**Требования:**
- Python 3.10+
- `openpyxl`, `PyMuPDF`, `pdf2image`
- `paddleocr` (опционально, для OCR уровня 2)

---

## Статус

- **Version:** 1.2
- **Last updated:** 2026-06-30
- **Integration:** smeta v3.0
- **Pipeline:** `[Чертежи] → [drawings-to-vor v1.2] → [ВОР.xlsx] → [smeta v3.0+] → [Смета]`

---

*Skill для LLM: процессный + automation helpers + OCR pipeline*
