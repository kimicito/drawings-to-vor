import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# Create figure
fig, ax = plt.subplots(1, 1, figsize=(16, 12))
ax.set_xlim(0, 16)
ax.set_ylim(0, 12)
ax.axis('off')

# Colors
color_input = '#E8F4FD'
color_process = '#FFF3E0'
color_output = '#E8F5E9'
color_data = '#F3E5F5'
color_arrow = '#1565C0'

def draw_box(ax, x, y, w, h, text, color, fontsize=10, bold=False):
    box = FancyBboxPatch((x, y), w, h, 
                         boxstyle="round,pad=0.1",
                         facecolor=color,
                         edgecolor='#333',
                         linewidth=1.5)
    ax.add_patch(box)
    weight = 'bold' if bold else 'normal'
    ax.text(x + w/2, y + h/2, text, ha='center', va='center',
            fontsize=fontsize, weight=weight, wrap=True)
    return box

def draw_arrow(ax, x1, y1, x2, y2, label='', color=color_arrow):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=2))
    if label:
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        ax.text(mid_x, mid_y + 0.2, label, ha='center', va='bottom',
                fontsize=8, style='italic', color='#555')

# Title
ax.text(8, 11.5, 'drawings-to-vor Pipeline', ha='center', va='center',
        fontsize=20, weight='bold', color='#1565C0')
ax.text(8, 11.1, 'TIFF → PDF → OCR → ВОР (Data Flow Diagram)', 
        ha='center', va='center', fontsize=12, color='#666')

# === INPUT ===
draw_box(ax, 0.5, 9, 2.5, 1.2, 'Исходные данные\n(TIFF, A0/A1/A2)', color_input, 9)
ax.text(1.75, 10.5, 'INPUT', ha='center', fontsize=9, weight='bold', color='#1976D2')

# TIFF properties
ax.text(1.75, 8.7, '• 300 DPI\n• Ч/Б скан\n• Большой\n  размер', 
        ha='center', va='top', fontsize=7, color='#555')

# === STAGE 1: CONVERT ===
draw_box(ax, 4, 9, 2.5, 1.2, 'tiff_to_pdf.py\nLossless конвертация', color_process, 9, bold=True)
draw_arrow(ax, 3, 9.6, 4, 9.6)

ax.text(5.25, 8.7, '• Без RAM\n• Потоковая\n• Сохраняет\n  DPI/размер',
        ha='center', va='top', fontsize=7, color='#555')

# === STAGE 2: PREPROCESS ===
draw_box(ax, 7.5, 9, 2.5, 1.2, 'preprocess.py\nНарезка тайлов', color_process, 9, bold=True)
draw_arrow(ax, 6.5, 9.6, 7.5, 9.6, 'PDF')

ax.text(8.75, 8.7, '• 1000×1000 px\n• Overlap 100px\n• Sharpen +\n  contrast',
        ha='center', va='top', fontsize=7, color='#555')

# === STAGE 3: OCR (split into two paths) ===
ax.text(8, 7.8, 'OCR API', ha='center', fontsize=10, weight='bold', color='#1565C0')

# Mistral path
draw_box(ax, 5.5, 6.5, 2.5, 1, 'Mistral Pixtral\npixtral-12b-2409', '#FFEBEE', 9)
draw_arrow(ax, 8.75, 8.3, 6.75, 7.5, 'PNG tiles', color='#C62828')
ax.text(6.75, 6.3, '$0.15-0.40/лист\n~1 мин', ha='center', fontsize=7, color='#C62828')

# Qwen path  
draw_box(ax, 9, 6.5, 2.5, 1, 'Alibaba Qwen-VL\nqwen-vl-ocr', '#E3F2FD', 9)
draw_arrow(ax, 9.5, 8.3, 10.25, 7.5, 'PNG tiles', color='#1565C0')
ax.text(10.25, 6.3, '$0.80-1.60/лист\n~2 мин', ha='center', fontsize=7, color='#1565C0')

# === STAGE 4: tile_ocr output ===
draw_box(ax, 7.5, 4.8, 2.5, 1.2, 'tile_ocr.py\nJSON + TXT + CSV', color_data, 9, bold=True)

# Arrows from OCR to output
draw_arrow(ax, 6.75, 6.5, 8, 6, '', color='#C62828')
draw_arrow(ax, 10.25, 6.5, 9, 6, '', color='#1565C0')

ax.text(8.75, 4.5, '• TEXT_LINES\n• DIMENSIONS\n• TABLES\n• CODES\n• GEOLOGY',
        ha='center', va='top', fontsize=7, color='#555')

# === STAGE 5: EXTRACT VOR ===
draw_box(ax, 7.5, 2.8, 2.5, 1.2, 'extract_vor.py\nАвто-расчёт ВОР', color_process, 9, bold=True)
draw_arrow(ax, 8.75, 4.8, 8.75, 4, 'OCR JSON', color='#2E7D32')

ax.text(8.75, 2.5, '• Формулы\n• Коэффициенты\n• Суммирование',
        ha='center', va='top', fontsize=7, color='#555')

# === OUTPUT ===
draw_box(ax, 7.5, 0.8, 2.5, 1.2, 'ВЕДОМОСТЬ ОБЪЁМОВ\nРАБОТ (ВОР)', color_output, 10, bold=True)
draw_arrow(ax, 8.75, 2.8, 8.75, 2, '', color='#2E7D32')

# Output formats
ax.text(11, 1.4, 'Форматы:\n• CSV\n• Excel\n• TXT', 
        ha='left', va='center', fontsize=8, color='#2E7D32')

# Side annotations - Data flow details
ax.text(13.5, 9.6, 'DATA FLOW', ha='center', fontsize=10, weight='bold', color='#333')

# Flow steps
flow_steps = [
    ('1', 'TIFF → PDF', 'Потоковая\nконвертация'),
    ('2', 'PDF → Tiles', '88-90 tiles\nна A1'),
    ('3', 'Tiles → OCR', 'Base64\nв API'),
    ('4', 'OCR → JSON', 'Структурированный\nвыход'),
    ('5', 'JSON → ВОР', 'Авто-расчёт\nобъёмов'),
]

y_pos = 8.8
for num, title, desc in flow_steps:
    ax.text(12.5, y_pos, f'{num}.', ha='center', va='center',
            fontsize=11, weight='bold', color='#1565C0',
            bbox=dict(boxstyle='circle', facecolor='#E3F2FD', edgecolor='#1565C0'))
    ax.text(13.2, y_pos + 0.15, title, ha='left', va='center',
            fontsize=9, weight='bold')
    ax.text(13.2, y_pos - 0.2, desc, ha='left', va='center',
            fontsize=7, color='#666')
    y_pos -= 1.5

# Legend
legend_y = 0.5
ax.text(0.5, legend_y, '■ Процесс', fontsize=8, color='#E65100')
ax.text(2.5, legend_y, '■ Данные', fontsize=8, color='#7B1FA2')
ax.text(4.3, legend_y, '■ Вход', fontsize=8, color='#1976D2')
ax.text(5.8, legend_y, '■ Выход', fontsize=8, color='#2E7D32')

# Draw colored squares for legend
colors = ['#FFF3E0', '#F3E5F5', '#E8F4FD', '#E8F5E9']
positions = [0.5, 2.5, 4.3, 5.8]
for color, pos in zip(colors, positions):
    rect = plt.Rectangle((pos - 0.15, legend_y - 0.08), 0.12, 0.15,
                         facecolor=color, edgecolor='#333', linewidth=0.5)
    ax.add_patch(rect)

plt.tight_layout()
plt.savefig('/root/.openclaw/workspace/projects/drawings-to-vor/output/pipeline_diagram.png', 
            dpi=200, bbox_inches='tight', facecolor='white')
print('Saved: pipeline_diagram.png')
