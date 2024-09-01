#!/bin/bash
CHECK_MARK="\033[0;32m\xE2\x9c\x94\033[0m"

echo -n "[...] Генерация файла ресурсов"
pyrcc5 -o resource_rc.py ui/resource.qrc
echo -e "\\r[ $CHECK_MARK ] Генерация файла ресурсов"

echo -n "[...] Генерация файла стиля"
pyrcc5 -o resource_rc.py ui/resource.qrc
mkdir -p gengui
rm -rf gengui/*
touch gengui/__init__.py

cd ui/
for file in *.ui
do
	INPUT="$file"
	OUTPUT="../gengui/ui_${file/.ui/.py}"
	python3 -m PyQt5.uic.pyuic -x $INPUT -o $OUTPUT
done
echo -e "\\r[ $CHECK_MARK ] Генерация файла стиля"
