prepare:
	python3 src/prepare_drawing.py --input $(INPUT) --output $(OUTPUT)

template:
	python3 src/create_vor_template.py

validate:
	python3 src/validate_vor.py --vor $(VOR) --drawing_pages $(PAGES)

install:
	pip install -r requirements.txt

.PHONY: prepare template validate install
