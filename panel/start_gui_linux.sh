#!/bin/bash

bash compile_gui.sh
echo "> Запуск утилиты сокрытия курсора..."
unclutter -idle 1 &
echo "> Запуск основного приложения..."
python3 panel_service.py PROD
