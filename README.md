# collector

Сборщик данных: слева поток камеры, справа панель выбора класса и состояний на русском.  
Управление: `1/2/3` — класс (ПЭТ/банка/посторонний), `s` — сохранить, `q`/`Esc` — выход.  
Поддержка кириллицы через Pillow и системный шрифт (`--font`).

## Установка
```bash
cd collector
python -m venv .venv && . .venv/bin/activate
pip install -e .
```

## Запуск
```bash
collector --cam 0 --w 1280 --h 720 --fps 30 \
  --pet states/states_pet.json \
  --can states/states_can.json \
  --foreign states/states_non_target.json \
  --out dataset \
  --font /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
```