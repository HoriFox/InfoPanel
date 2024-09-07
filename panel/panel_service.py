#!/bin/python3

import sys
import os
import time
from access import WEATHER_API_KEY_ACCESS

RELEASE_PROD = (False if sys.argv[1] == "DEV" else True) if len(sys.argv) > 1 else True

import requests
import logging
import pathlib
import threading

# from PyQt5.QtMultimedia import QSound

if RELEASE_PROD:
    import serial
    import wiringpi
    from wiringpi import GPIO, HIGH, LOW
    from lib.aht20 import AHT20
    from lib.bmp_280 import BMP280
    from lib.ky_040 import Encoder
    # from lib.ads_1x15 import ADS1115

from PyQt5.QtWidgets import QApplication, QWidget, QGraphicsDropShadowEffect, QShortcut
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import QPixmap, QColor, QKeySequence
from PyQt5.QtCore import QTimer, Qt, QDateTime

from gengui import ui_window

LOG_LEVEL = logging.DEBUG
LOG_FILE = 'infopanel.log'

logFormatter = logging.Formatter("[%(asctime)s] [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
log = logging.getLogger()
log.setLevel(LOG_LEVEL)
fileHandler = logging.FileHandler(LOG_FILE)
fileHandler.setFormatter(logFormatter)
log.addHandler(fileHandler)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
log.addHandler(consoleHandler)

WORK_DIR = pathlib.Path(__file__).parent.resolve()

# Настройки DEV размеров отображения (можно настроить)
DEV_WIDTH_SIZE = 388
DEV_HEIGHT_SIZE = 690

# Настройки работы погоды (можно настроить)
WEATHER_URL = "http://api.openweathermap.org/data/2.5/weather"
WEATHER_API_KEY = WEATHER_API_KEY_ACCESS
WEATHER_UPDATE = False
CITY_ID = 524901  # 'Moscow,RU'
WEATHER_TIME_UPDATE = 'обновлено %s мин назад'
CONVERT_HPA_MMHG = 0.7506

# Датчик движения SR602 (можно настроить)
SENSOR_SR602_PIN = 13  # GPIO2_D4
SLEEP_ACTION = False  # Работа с датчиком движения, уход в сон и пробуждение
DELAY_OFF = 20  # Время ожидания без движения

# Высоковольтное реле (можно настроить)
RELAY_PIN = 4  # GPIO4_A4
BACKLIGHT_ACTION = True  # Работа с подсветкой, отключение/включения подстветки для исключения выгорания дисплея

# Энкодер KY040 (можно настроить)
STEP_SENSITIVITY = 4
BUTTON_KY040_PIN = 11  # SPI4_TXD
ROTATE_KY040_PIN = 12  # SPI4_RXD
CLK_KY040_PIN = 14  # SPI4_CLK

# Адреса i2c датчиков (можно настроить)
BMP280_ADDRESS = 0x77
AHT20_ADDRESS = 0x38
ADS1115_ADDRESS = 0x48

# Путь к uarl порту общения с arduino
UART_URL = "/dev/ttyS1"
HEIL_COMMAND = b"heil\r\n"
LOADING_COMMAND = b"loading\r\n"
LOADING_END_COMMAND = b"loading_end\r\n"
DATA_COMMAND = b"data\r\n"

RESTART_PANEL = "restart_panel"
POWER_OFF_PANEL = "power_off_panel"
RESTART_PO = "restart_po"
DIAGNOSTIC_PO = "diagnostic_po"
CLOSE_OPTIONS = "close_options"


class LinkedDictItem:
    def __init__(self, value, _previous=None, _next=None):
        self.previous = _previous
        self.next = _next
        self.value = value

    def getPreviousKey(self):
        return self.previous

    def getNextKey(self):
        return self.next

    def getValue(self):
        return self.value


class App(QWidget):
    dev_screen_width = 388
    dev_screen_height = 690
    k_width = 1
    k_height = 1
    week_ru = {"Monday": "Понедельник", "Tuesday": "Вторник",
               "Wednesday": "Среда", "Thursday": "Четверг",
               "Friday": "Пятница", "Saturday": "Суббота", "Sunday": "Воскресенье"}
    # sound_startup = QSound("%s/src/resource/startup.wav" % WORK_DIR)

    # Технические переменные не требующие изменения
    timeout_on_tv = DELAY_OFF
    weather_update_timestamp = 0
    visible = True
    bmp_sensor = None
    aht20_sensor = None
    ky040_thread = None
    serial = None
    timer_fixed_update = None
    timer_minute_fixed_update = None
    timer_weather = None
    screen_width = 0
    screen_height = 0
    button_list = {}
    current_button_select = None
    encoder_semaphore = False
    encoder_current_pos = 0
    options_container_show = False


    def __init__(self, app_object: QApplication):
        super().__init__()
        screen = app_object.primaryScreen()
        size = screen.size()

        self.ui = ui_window.Ui_Form()
        self.ui.setupUi(self)
        self.setWindowIcon(QtGui.QIcon('%s/icon.ico' % WORK_DIR))

        # Запечём все переходы между кнопками, пусть и массивно
        # TODO: Сделать как-то более аккуратно
        self.button_list[self.ui.restart_panel_button] = LinkedDictItem(value=RESTART_PANEL,
                                                                        _previous=self.ui.close_option_button,
                                                                        _next=self.ui.poweroff_panel_button)
        self.button_list[self.ui.poweroff_panel_button] = LinkedDictItem(value=POWER_OFF_PANEL,
                                                                         _previous=self.ui.restart_panel_button,
                                                                         _next=self.ui.restart_po_button)
        self.button_list[self.ui.restart_po_button] = LinkedDictItem(value=RESTART_PO,
                                                                     _previous=self.ui.poweroff_panel_button,
                                                                     _next=self.ui.diagnostic_button)
        self.button_list[self.ui.diagnostic_button] = LinkedDictItem(value=DIAGNOSTIC_PO,
                                                                     _previous=self.ui.restart_po_button,
                                                                     _next=self.ui.close_option_button)
        self.button_list[self.ui.close_option_button] = LinkedDictItem(value=CLOSE_OPTIONS,
                                                                       _previous=self.ui.diagnostic_button,
                                                                       _next=self.ui.restart_panel_button)
        self.current_button_select = self.ui.close_option_button
        self.set_button_select(self.current_button_select, True)
        self.ui.diagnostic_container.setCurrentIndex(0)
        self.ui.options_container.show() if self.options_container_show else self.ui.options_container.hide()

        if not RELEASE_PROD:
            self.multi_log('ПО панели в режиме разработки!')

        if RELEASE_PROD:
            self.serial = serial.Serial(UART_URL, 9600, timeout=1)
            self.send_command(command=LOADING_END_COMMAND)

            wiringpi.wiringPiSetup()
            wiringpi.pinMode(SENSOR_SR602_PIN, GPIO.INPUT)
            wiringpi.pinMode(RELAY_PIN, GPIO.OUTPUT)

            # wiringpi.pinMode(15, GPIO.OUTPUT)
            # wiringpi.digitalWrite(15, LOW)

            # self.ads_board = ADS1115(busId=1, address=ADS1115_ADDRESS)
            # self.ads_board.setGain(self.ads_board.PGA_6_144V)
            # self.convert_volt = self.ads_board.toVoltage()

            # Убираем сигнал на обрывающее подсветку реле
            wiringpi.digitalWrite(RELAY_PIN, LOW)

            self.bmp_sensor = BMP280(port=1,
                                     addr=BMP280_ADDRESS,
                                     mode=BMP280.NORMAL_MODE,
                                     oversampling_p=BMP280.OVERSAMPLING_P_x16,
                                     oversampling_t=BMP280.OVERSAMPLING_T_x4,
                                     filter=BMP280.IIR_FILTER_x2,
                                     standby=BMP280.T_STANDBY_1000)

            self.aht20_sensor = AHT20(addr=AHT20_ADDRESS)

            encoder = Encoder(CLK=CLK_KY040_PIN, DT=ROTATE_KY040_PIN, SW=BUTTON_KY040_PIN, polling_interval=1,
                              inc_callback=self.encoder_inc, dec_callback=self.encoder_dec,
                              sw_callback=self.encoder_button, sw_debounce_time=100)

            self.ky040_thread = threading.Thread(target=encoder.watch)
            self.ky040_thread.start()
        else:
            self.inc_shortcut = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_PageDown), self)
            self.inc_shortcut.activated.connect(self.encoder_inc)
            self.dec_shortcut = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_PageUp), self)
            self.dec_shortcut.activated.connect(self.encoder_dec)
            self.click_shortcut = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_Space), self)
            self.click_shortcut.activated.connect(self.encoder_button)

        self.calculation_size(size)

        # Добавляем красивость в виде тени на UI элементы
        # for element in [self.ui.weather_container, self.ui.debug_container,
        #                 self.ui.home_info_container, self.ui.diagnostic_panel,
        #                 self.ui.options_panel]:
        #     shadow = QGraphicsDropShadowEffect()
        #     shadow.setBlurRadius(16)
        #     shadow.setColor(QColor(0, 0, 0, 128))
        #     shadow.setXOffset(8)
        #     shadow.setYOffset(8)
        #     element.setGraphicsEffect(shadow)

        self.ui.weather_container.setCurrentIndex(0)
        self.ui.home_info_container.setCurrentIndex(0)

        self.init_timers()
        # Принудительные предварительные обновления нужных панелей перед показом
        self.update_weather()
        self.update_met_sensor()
        # self.update_news()
        self.fixed_update()

        # self.sound_startup.play()

        self.show()

    def exec_option(self, option):
        if option == RESTART_PANEL:
            self.multi_log('Run RESTART_PANEL')
            if RELEASE_PROD:
                os.system("reboot 0")
        elif option == POWER_OFF_PANEL:
            self.multi_log('Run POWER_OFF_PANEL')
            if RELEASE_PROD:
                os.system("shutdown 0")
        elif option == RESTART_PO:
            self.multi_log('Run RESTART_PO')
            if RELEASE_PROD:
                os.system("systemctl restart panel")
        elif option == DIAGNOSTIC_PO:
            self.multi_log('Run DIAGNOSTIC_PO')
            self.ui.diagnostic_container.setCurrentIndex(1)
            self.diagnostic()
        elif option == CLOSE_OPTIONS:
            self.show_options_container(is_show=False)

    def diagnostic(self):
        self.ui.diagnostic_text.setPlainText("TEST")

    def set_button_select(self, ui_element, select=False):
        ui_element.setProperty("select", select)
        ui_element.style().polish(ui_element)

    def show_options_container(self, is_show=True):
        self.ui.options_container.show() if is_show else self.ui.options_container.hide()
        self.options_container_show = is_show

    def encoder_inc(self, pos=0):
        """
        Callback метод вращения энкодера KY-040 по часовой стрелке
        :param pos: 0-100 позиция высчитанного положения
        """
        self.show_options_container()
        if self.encoder_semaphore or pos - self.encoder_current_pos < STEP_SENSITIVITY:
            return
        self.encoder_semaphore = True
        self.encoder_current_pos = pos
        self.ui.diagnostic_container.setCurrentIndex(0)
        self.set_button_select(self.current_button_select, False)
        self.current_button_select = self.button_list[self.current_button_select].getNextKey()
        self.set_button_select(self.current_button_select, True)
        self.multi_log(self.button_list[self.current_button_select].getValue())
        time.sleep(0.2)
        self.encoder_semaphore = False

    def encoder_dec(self, pos=0):
        """
        Callback метод вращения энкодера KY-040 против часовой стрелке
        :param pos: 0-100 позиция высчитанного положения
        """
        self.show_options_container()
        if self.encoder_semaphore or self.encoder_current_pos - pos < STEP_SENSITIVITY:
            return
        self.encoder_semaphore = True
        self.encoder_current_pos = pos
        self.ui.diagnostic_container.setCurrentIndex(0)
        self.set_button_select(self.current_button_select, False)
        self.current_button_select = self.button_list[self.current_button_select].getPreviousKey()
        self.set_button_select(self.current_button_select, True)
        self.multi_log(self.button_list[self.current_button_select].getValue())
        time.sleep(0.2)
        self.encoder_semaphore = False

    def encoder_button(self):
        """
        Callback метод нажатия на энкодер KY-040
        """
        if not self.options_container_show:
            self.show_options_container()
            return
        if self.encoder_semaphore:
            return
        self.encoder_semaphore = True
        option = self.button_list[self.current_button_select].getValue()
        self.exec_option(option)
        time.sleep(0.2)
        self.encoder_semaphore = False

    def send_command(self, command=HEIL_COMMAND):
        if RELEASE_PROD:
            self.serial.write(command)

    def calculation_size(self, size):
        """
        Метод авто масштабирования окна и рассчёта коэффициента масштабирования
        :param size: tuple текущего размера монитора
        """
        # TODO: Что-то придумать с автоматический scale шрифтов

        self.screen_width = size.width() if RELEASE_PROD else DEV_WIDTH_SIZE
        self.screen_height = size.height() if RELEASE_PROD else DEV_HEIGHT_SIZE

        self.k_width = self.screen_width / self.dev_screen_width
        self.k_height = self.screen_height / self.dev_screen_height
        self.setWindowFlag(Qt.FramelessWindowHint)
        # self.showMaximized()
        self.multi_log('Коэффициент масштабирования - c_width: %s, c_height: %s'
                       % (round(self.k_width, 3), round(self.k_height, 3)))
        self.multi_log('Размер окна - width: %s, height: %s'
                       % (self.screen_width, self.screen_height))
        self.resize(self.screen_width, self.screen_height)
        self.ui.date_widget.setStyleSheet(self.ui.date_widget.styleSheet() + "font-size: %spx;" % self.fix(20))
        self.ui.time_widget.setStyleSheet(self.ui.time_widget.styleSheet() + "font-size: %spx;" % self.fix(55))
        self.ui.weather_text_1.setStyleSheet(self.ui.weather_text_1.styleSheet() + "font-size: %spx;" % self.fix(10))
        self.ui.weather_text_2.setStyleSheet(self.ui.weather_text_2.styleSheet() + "font-size: %spx;" % self.fix(10))
        self.ui.weather_text_3.setStyleSheet(self.ui.weather_text_3.styleSheet() + "font-size: %spx;" % self.fix(16))
        self.ui.weather_text_4.setStyleSheet(self.ui.weather_text_4.styleSheet() + "font-size: %spx;" % self.fix(10))
        self.ui.weather_time_update_text.setStyleSheet(
            self.ui.weather_time_update_text.styleSheet() + "font-size: %spx;" % self.fix(7))
        self.ui.update_weather_label.setStyleSheet(self.ui.update_weather_label.styleSheet() + "font-size: %spx;"
                                                   % self.fix(10))

        self.ui.home_info_container.setMinimumWidth(self.fix(130))
        self.ui.home_info_container.setMaximumWidth(self.fix(130))
        self.ui.down_container.setMinimumHeight(self.fix(130))
        self.ui.down_container.setMaximumHeight(self.fix(130))
        self.ui.options_panel.setMinimumWidth(self.fix(100))
        self.ui.options_panel.setMaximumWidth(self.fix(100))
        self.ui.up_container.setMinimumHeight(self.fix(120))
        self.ui.up_container.setMaximumHeight(self.fix(120))
        self.ui.home_info_label.setStyleSheet(self.ui.home_info_label.styleSheet() + "font-size: %spx;" % self.fix(16))
        self.ui.pressure_label.setStyleSheet(self.ui.pressure_label.styleSheet() + "font-size: %spx;" % self.fix(10))
        self.ui.pressure_value.setStyleSheet(self.ui.pressure_value.styleSheet() + "font-size: %spx;" % self.fix(10))
        self.ui.temperature_label.setStyleSheet(self.ui.temperature_label.styleSheet() + "font-size: %spx;"
                                                % self.fix(10))
        self.ui.temperature_value.setStyleSheet(self.ui.temperature_value.styleSheet() + "font-size: %spx;"
                                                % self.fix(10))
        self.ui.humidity_label.setStyleSheet(self.ui.humidity_label.styleSheet() + "font-size: %spx;" % self.fix(10))
        self.ui.humidity_value.setStyleSheet(self.ui.humidity_value.styleSheet() + "font-size: %spx;" % self.fix(10))
        self.ui.update_home_info_label.setStyleSheet(self.ui.update_home_info_label.styleSheet() + "font-size: %spx;"
                                                     % self.fix(10))

    def init_timers(self):
        self.timer_fixed_update = QTimer()
        self.timer_fixed_update.setInterval(1000)  # 1 sec
        self.timer_fixed_update.timeout.connect(self.fixed_update)
        self.timer_fixed_update.start()

        self.timer_minute_fixed_update = QTimer()
        self.timer_minute_fixed_update.setInterval(60 * 1000)  # 1 min
        self.timer_minute_fixed_update.timeout.connect(self.minute_fixed_update)
        self.timer_minute_fixed_update.start()

        self.timer_weather = QTimer()
        self.timer_weather.setInterval(30 * 60 * 1000)  # 30 min
        self.timer_weather.timeout.connect(self.half_hour_fixed_update)
        self.timer_weather.start()

    def multi_log(self, *message):
        """
        Метод вывода в UI, cli и текстовой лог
        :param message: сообщение для вывода в лог
        """
        print_mes = ' '.join(map(str, message))
        log.debug(print_mes)
        self.ui.debug_widget.setText(print_mes)

    def fixed_update(self):
        """
        Метод фиксированного обновления каждую 1 секунду
        """
        # self.send_command(command=LOADING_COMMAND)

        # wiringpi.digitalWrite(15, HIGH)
        # sleep(0.280)
        # val_0 = self.ads_board.readADC(0)
        # val_1 = self.ads_board.readADC(1)
        # val_2 = self.ads_board.readADC(2)
        # val_3 = self.ads_board.readADC(3)

        # self.multi_log("Analog0: {0:d}\t{1:.3f} V".format(val_0, val_0 * self.convert_volt))
        # self.multi_log("Analog1: {0:d}\t{1:.3f} V".format(val_1, val_1 * self.convert_volt))
        # self.multi_log("Analog2: {0:d}\t{1:.3f} V".format(val_2, val_2 * self.convert_volt))
        # self.multi_log("Analog3: {0:d}\t{1:.3f} V".format(val_3, val_3 * self.convert_volt))

        # sleep(0.40)
        # wiringpi.digitalWrite(15, LOW)
        #
        # self.multi_log("0.17 * val_0(%s) * self.convert_volt(%s) - 0.1" % (val_0, self.convert_volt))
        # dust0 = 0.17 * val_0 * self.convert_volt - 0.1
        # self.multi_log("Analog0: {0:d}\t{1:.3f} V".format(val_0, dust0))
        #
        # self.multi_log("0.17 * val_1(%s) * self.convert_volt(%s) - 0.1" % (val_3, self.convert_volt))
        # dust3 = 0.17 * val_3 * self.convert_volt - 0.1
        # self.multi_log("Analog1: {0:d}\t{1:.3f} V".format(val_3, dust3))

        if SLEEP_ACTION and RELEASE_PROD:
            if wiringpi.digitalRead(SENSOR_SR602_PIN):
                self.multi_log('Замечено движение!')
                # Восстанавливаем таймер
                self.timeout_on_tv = DELAY_OFF
                if not self.visible:
                    self.show_panel()
            elif self.timeout_on_tv > 0:
                self.timeout_on_tv -= 1
                # self.multi_log('До засыпания: %s' % self.timeout_on_tv)
                if self.timeout_on_tv == 0 and self.visible:
                    self.hide_panel()

        self.update_date_time()

    def minute_fixed_update(self):
        """
        Метод фиксированного обновления каждую 1 минуту
        """
        self.send_command(command=LOADING_COMMAND)
        self.weather_update_timestamp += 1
        self.ui.weather_time_update_text.setText(WEATHER_TIME_UPDATE % self.weather_update_timestamp)
        self.update_met_sensor()

    def half_hour_fixed_update(self):
        """
        Метод фиксированного обновления каждые 30 минут
        """
        self.send_command(command=LOADING_COMMAND)
        self.update_weather()

    def update_met_sensor(self):
        """
        Метод обновления метео сенсора AHT20+BMP280
        """
        # Работает только в режиме PROD вместе с датчиками
        if not RELEASE_PROD:
            return
        try:
            humidity = self.aht20_sensor.get_humidity()
            pressure_hpa = self.bmp_sensor.read_pressure()
            pressure_mmhg = pressure_hpa * CONVERT_HPA_MMHG
            temp_bmp280 = self.bmp_sensor.read_temperature()

            self.ui.pressure_value.setText("%s hPa - %s мм рт.ст." % (round(pressure_hpa), round(pressure_mmhg)))
            self.ui.temperature_value.setText("%s °C" % round(temp_bmp280))
            self.ui.humidity_value.setText("%s %%" % round(humidity))

            self.ui.home_info_container.setCurrentIndex(1)
        except Exception as err:
            self.multi_log("[ERROR] Ошибка:", err)
            self.ui.home_info_container.setCurrentIndex(0)

    def show_panel(self):
        """
        Метод пробуждения панели из спящего режима
        """
        self.multi_log('Пробуждаемся!')
        self.visible = True
        self.ui.container.show()
        if BACKLIGHT_ACTION:
            # Убираем сигнал на обрывающее подсветку реле
            wiringpi.digitalWrite(RELAY_PIN, LOW)
            # self.sound_startup.play()

    def hide_panel(self):
        """
        Метод входа панели в спящий режим
        """
        self.multi_log('Засыпаем!')
        self.visible = False
        self.ui.container.hide()
        if BACKLIGHT_ACTION:
            # Падаём сигнал на обрывающее подсветку реле
            wiringpi.digitalWrite(RELAY_PIN, HIGH)

    def update_date_time(self):
        """
        Метод обновления панели даты и времени
        """
        time = QDateTime.currentDateTime()
        date_time_display = time.toString('hh:mm:ss|dd.MM.yyyy|dddd').split('|')
        date_time_display[1] += " %s" % (self.week_ru[date_time_display[2]]
                                         if self.week_ru.__contains__(date_time_display[2]) else date_time_display[2])
        self.ui.time_widget.setText(date_time_display[0])
        self.ui.date_widget.setText(date_time_display[1])

    def update_weather(self):
        """
        Метод обновления панели погоды
        """
        if WEATHER_UPDATE:
            self.multi_log('Погода обновляется')
            try:
                res = requests.get(WEATHER_URL,
                                   params={'id': CITY_ID, 'units': 'metric', 'lang': 'ru', 'APPID': WEATHER_API_KEY},
                                   timeout=2)
                data = None
                if res is not None:
                    data = res.json()
                if data is not None:
                    pixmap = QPixmap('%s/src/resource/weather_pack/%s.png' % (WORK_DIR, data['weather'][0]['icon']))
                    print('%s/src/resource/weather_pack/%s.png' % (WORK_DIR, data['weather'][0]['icon']))
                    pixmap = pixmap.scaled(self.fix(90), self.fix(90), QtCore.Qt.KeepAspectRatio)
                    self.ui.weather_img.setPixmap(pixmap)

                    self.ui.weather_text_1.setText(data['weather'][0]['description'])
                    self.ui.weather_text_2.setText("%s..." % round(data['main']['temp_min']))
                    self.ui.weather_text_3.setText("%s" % round(data['main']['temp']))
                    self.ui.weather_text_4.setText("...%s" % round(data['main']['temp_max']))

                    self.weather_update_timestamp = 0
                    self.ui.weather_time_update_text.setText(WEATHER_TIME_UPDATE % "0")

                    self.ui.weather_container.setCurrentIndex(1)
            except requests.exceptions.Timeout as e:
                self.multi_log("[ERROR] Ошибка: Превышено время ожидания сервиса!", e)
                self.ui.weather_container.setCurrentIndex(0)
            except Exception as e:
                self.multi_log("[ERROR] Ошибка:", e)
                self.ui.weather_container.setCurrentIndex(0)

    def fix(self, size, side='w'):
        """
        Метод расчёта размера UI элемента
        :param size: размер, который нужно пересчитать
        :param side: выбор {w, h} - сторона по которой будет произведён расчёт
        """
        if type(size) == list:
            return tuple(map(lambda x: round(x * self.k_width if side == 'w' else self.k_height), size))
        else:
            return round(size * self.k_width if side == 'w' else self.k_height)


if __name__ == "__main__":
    app = None
    try:
        app = QApplication(sys.argv)
        app_window = App(app_object=app)
    except KeyboardInterrupt:
        pass
    if app:
        sys.exit(app.exec_())
