<img src="https://github.com/HoriFox/SmartHomeCentralDoc/blob/main/gitimg/infopanel_logo.png" width="500">

## InfoPanel - Инфо-панель (время, погода и т.д.)

<img src="https://github.com/HoriFox/InfoPanel/blob/master/img/InfoPanelVisual.png" width="500">

#### Файл ключей  
```bash
# В директории `panel` создать файл `access.py`
WEATHER_API_KEY_ACCESS = "[КЛЮЧ]"
```

#### Запуск на конечном АРМ (Linux)  
Из директории файла: `start_gui_linux.sh`

#### Запуск на конечном АРМ (Win)  
Из директории файла: `start_gui_win.sh`

#### Настройки запуска в PyCharm (Win)  
Запуск удалённо (REMOTE_START):  
Script path: `[LOCAL]/InfoPanel/panel/start_gui_remote.sh`  
Working directory: `[LOCAL]/InfoPanel/panel`  
Interpreter path: `C:\Program Files\Git\bin\sh.exe`  

DEV запуск на АРМ (START):  
Script path: `[LOCAL]/InfoPanel/panel/start_gui_win.sh`  
Working directory и Interpreter path соответствующие  

#### Схема подключения переферии
![Схема](https://github.com/HoriFox/InfoPanel/blob/master/img/InfoPanel.png)
