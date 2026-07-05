import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
import numpy as np

def save_fig(fig, name):
    path = f'/root/.openclaw/workspace/projects/drawings-to-vor/output/{name}.png'
    fig.savefig(path, dpi=200, bbox_inches='tight', facecolor='white')
    print(f'Saved: {name}.png')

# ============================================================
# A) SEQUENCE DIAGRAM
# ============================================================
fig, ax = plt.subplots(1, 1, figsize=(14, 10))
ax.set_xlim(0, 14)
ax.set_ylim(0, 10)
ax.axis('off')

ax.text(7, 9.5, 'Sequence Diagram: TIFF → ВОР', ha='center', fontsize=16, weight='bold', color='#1565C0')

# Actors
actors = [
    (1.5, 'User\n(Сметчик)', '#E3F2FD'),
    (4.5, 'tiff_to_pdf.py', '#FFF3E0'),
    (7.5, 'preprocess.py', '#FFF3E0'),
    (10.5, 'tile_ocr.py', '#FFF3E0'),
    (13, 'extract_vor.py', '#E8F5E9'),
]

for x, name, color in actors:
    rect = FancyBboxPatch((x-0.8, 8.2), 1.6, 0.8, boxstyle="round,pad=0.05",
                          facecolor=color, edgecolor='#333', linewidth=1.5)
    ax.add_patch(rect)
    ax.text(x, 8.6, name, ha='center', va='center', fontsize=8, weight='bold')
    # Lifeline
    ax.plot([x, x], [8.2, 0.5], 'k--', linewidth=0.8, alpha=0.5)

# Messages
messages = [
    (1.5, 4.5, 7.5, '1: TIFF файл'),
    (4.5, 7.5, 6.8, '2: PDF (lossless)'),
    (7.5, 10.5, 6.0, '3: PNG tiles (1000×1000)'),
    (10.5, 10.5, 5.0, '4: POST /chat/completions\n(base64 image)'),
    (10.5, 10.5, 4.0, '5: Response (JSON markdown)'),
    (10.5, 13, 3.0, '6: OCR JSON'),
    (13, 13, 2.0, '7: Calculate volumes\n(π×r²×h)'),
    (13, 1.5, 1.0, '8: ВОР (CSV/Excel/TXT)'),
]

for x1, x2, y, text in messages:
    color = '#1565C0' if x1 != x2 else '#2E7D32'
    ax.annotate('', xy=(x2, y), xytext=(x1, y),
                arrowprops=dict(arrowstyle='->', color=color, lw=1.5))
    ax.text((x1+x2)/2, y+0.15, text, ha='center', va='bottom', fontsize=7, color='#333')

# Qwen API box
api_rect = FancyBboxPatch((9.5, 4.5), 2, 1, boxstyle="round,pad=0.1",
                          facecolor='#E1F5FE', edgecolor='#0277BD', linewidth=2)
ax.add_patch(api_rect)
ax.text(10.5, 5.2, 'Alibaba Qwen-VL\nAPI', ha='center', va='center', fontsize=8, weight='bold', color='#0277BD')
ax.annotate('', xy=(10.5, 5.5), xytext=(10.5, 5.0), arrowprops=dict(arrowstyle='->', color='#0277BD', lw=1.5))
ax.annotate('', xy=(10.5, 4.5), xytext=(10.5, 4.0), arrowprops=dict(arrowstyle='->', color='#0277BD', lw=1.5))

save_fig(fig, 'diagram_sequence')
plt.close()

# ============================================================
# B) ARCHITECTURE DIAGRAM
# ============================================================
fig, ax = plt.subplots(1, 1, figsize=(14, 10))
ax.set_xlim(0, 14)
ax.set_ylim(0, 10)
ax.axis('off')

ax.text(7, 9.5, 'Architecture: drawings-to-vor Components', ha='center', fontsize=16, weight='bold', color='#1565C0')

# Layers
layers = [
    ('Input Layer', 8.5, '#E3F2FD'),
    ('Processing Layer', 6.5, '#FFF3E0'),
    ('API Layer', 4.5, '#E1F5FE'),
    ('Output Layer', 2.5, '#E8F5E9'),
]

for label, y, color in layers:
    ax.text(0.5, y+0.8, label, fontsize=10, weight='bold', color='#555')
    rect = Rectangle((0.3, y-0.3), 13.4, 1.8, facecolor=color, edgecolor='#999', 
                     linewidth=1, alpha=0.3, linestyle='--')
    ax.add_patch(rect)

# Components
components = [
    # Input
    (2, 8.5, 'TIFF Scan\n(300 DPI, A1)', '#E3F2FD'),
    (5, 8.5, 'PDF Output\n(lossless)', '#E3F2FD'),
    (8, 8.5, 'PNG Tiles\n(1000×1000)', '#E3F2FD'),
    
    # Processing
    (2, 6.5, 'tiff_to_pdf.py\nStreaming', '#FFF3E0'),
    (5, 6.5, 'preprocess.py\nSharpen + Tile', '#FFF3E0'),
    (8, 6.5, 'tile_ocr.py\nQwen-VL OCR', '#FFF3E0'),
    (11, 6.5, 'extract_vor.py\nCalculate', '#FFF3E0'),
    
    # API
    (7, 4.5, 'Alibaba Qwen-VL-OCR\nAPI (base64)', '#E1F5FE'),
    
    # Output
    (3, 2.5, 'JSON\n(raw OCR)', '#E8F5E9'),
    (6, 2.5, 'TXT\n(human readable)', '#E8F5E9'),
    (9, 2.5, 'CSV\n(tables)', '#E8F5E9'),
    (12, 2.5, 'Excel\n(ВОР)', '#E8F5E9'),
]

for x, y, text, color in components:
    rect = FancyBboxPatch((x-0.9, y-0.4), 1.8, 0.9, boxstyle="round,pad=0.05",
                          facecolor=color, edgecolor='#333', linewidth=1.2)
    ax.add_patch(rect)
    ax.text(x, y, text, ha='center', va='center', fontsize=7.5)

# Arrows
arrows = [
    (2, 8.0, 2, 7.1),    # TIFF → tiff_to_pdf
    (2, 6.0, 5, 6.9),    # tiff → preprocess
    (5, 8.0, 5, 7.1),    # PDF → preprocess
    (5, 6.0, 8, 6.9),    # preprocess → tile_ocr
    (8, 8.0, 8, 7.1),    # tiles → tile_ocr
    (8, 6.0, 7.5, 5.0),  # tile_ocr → Qwen API
    (7.5, 4.0, 8, 7.1),  # Qwen → tile_ocr
    (8, 6.0, 11, 6.9),   # tile_ocr → extract_vor
    (11, 6.0, 12, 2.9),  # extract_vor → Excel
    (8, 6.0, 9, 2.9),    # tile_ocr → CSV
    (8, 6.0, 6, 2.9),    # tile_ocr → TXT
    (8, 6.0, 3, 2.9),    # tile_ocr → JSON
]

for x1, y1, x2, y2 in arrows:
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color='#666', lw=1, connectionstyle="arc3,rad=0.1"))

# Data store
data_rect = FancyBboxPatch((11.5, 4), 1.8, 1, boxstyle="round,pad=0.05",
                           facecolor='#F3E5F5', edgecolor='#7B1FA2', linewidth=1.5)
ax.add_patch(data_rect)
ax.text(12.4, 4.5, 'Data Store\n(.env keys)', ha='center', va='center', fontsize=7, color='#7B1FA2')
ax.annotate('', xy=(11.2, 6.1), xytext=(11.8, 5.1), arrowprops=dict(arrowstyle='->', color='#7B1FA2', lw=1))

save_fig(fig, 'diagram_architecture')
plt.close()

# ============================================================
# C) PROCESS FLOW (для сметчика)
# ============================================================
fig, ax = plt.subplots(1, 1, figsize=(12, 14))
ax.set_xlim(0, 12)
ax.set_ylim(0, 14)
ax.axis('off')

ax.text(6, 13.5, 'Process Flow: Как сметчику получить ВОР', ha='center', fontsize=16, weight='bold', color='#1565C0')
ax.text(6, 13.1, 'из TIFF-скана за 4 шага', ha='center', fontsize=11, color='#666')

# Steps
steps = [
    (13.0, 'ШАГ 1: Подготовка', '#E3F2FD',
     '• Получить TIFF-скан чертежа (300 DPI)\n• Проверить читаемость текста\n• Сохранить ключи в .env:\n  DASHSCOPE_API_KEY=sk-xxx'),
    
    (10.5, 'ШАГ 2: Конвертация и нарезка', '#FFF3E0',
     '• TIFF → PDF (без потери качества)\n• PDF → PNG тайлы 1000×1000\n• ~80 тайлов на лист A1\n• Координаты в имени файла'),
    
    (7.5, 'ШАГ 3: OCR (распознавание)', '#E1F5FE',
     '• Отправить тайлы в Qwen-VL-OCR\n• Получить JSON с текстом\n• Автопарсинг таблиц\n• Сохранить: ocr_result.json'),
    
    (4.5, 'ШАГ 4: Расчёт ВОР', '#E8F5E9',
     '• Запустить extract_vor.py\n• Авто-расчёт объёмов:\n  - Сваи: π×r²×h×n\n  - Бетон, арм., выбурка\n• Получить Excel + CSV + TXT'),
    
    (1.5, 'РЕЗУЛЬТАТ', '#C8E6C9',
     '✅ Ведомость объёмов работ\n✅ Готовая сметная документация\n✅ Импорт в Гранд/Смета.ру'),
]

for y, title, color, text in steps:
    # Title box
    rect = FancyBboxPatch((1, y+0.3), 10, 0.7, boxstyle="round,pad=0.05",
                          facecolor=color, edgecolor='#333', linewidth=1.5)
    ax.add_patch(rect)
    ax.text(6, y+0.65, title, ha='center', va='center', fontsize=11, weight='bold')
    
    # Content box
    rect2 = FancyBboxPatch((1, y-1.3), 10, 1.5, boxstyle="round,pad=0.05",
                           facecolor='white', edgecolor='#999', linewidth=1)
    ax.add_patch(rect2)
    ax.text(6, y-0.5, text, ha='center', va='center', fontsize=9, color='#333')
    
    # Arrow down
    if y > 2:
        ax.annotate('', xy=(6, y-1.5), xytext=(6, y+0.2),
                    arrowprops=dict(arrowstyle='->', color='#1565C0', lw=2))

# Time estimate
ax.text(6, 0.3, '⏱ Общее время: ~5-10 мин на лист (из них ~2 мин OCR)', 
        ha='center', fontsize=10, style='italic', color='#666',
        bbox=dict(boxstyle='round', facecolor='#FFFDE7', edgecolor='#FBC02D'))

save_fig(fig, 'diagram_process_flow')
plt.close()

print("\nAll 3 diagrams created!")
