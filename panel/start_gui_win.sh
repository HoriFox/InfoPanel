#!/bin/bash

bash compile_gui_win.sh
echo "[...] Запуск"
python panel_service.py DEV
