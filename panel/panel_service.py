#!/bin/python3

import sys
from access import WEATHER_API_KEY_ACCESS

RELEASE_PROD = (False if sys.argv[1] == "DEV" else True) if len(sys.argv) > 1 else True

import requests
import logging
import pathlib
import threading
# from PyQt5.QtMultimedia import QSound

if RELEASE_PROD:
    import wiringpi
    from wiringpi import GPIO, HIGH, LOW
    from lib.aht20 import AHT20
    from lib.bmp_280 import BMP280
    from lib.ky_040 import Encoder
    # from lib.ads_1x15 import ADS1115

from PyQt5.QtWidgets import QApplication, QWidget, QGraphicsDropShadowEffect
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import QPixmap, QColor
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
WEATHER_UPDATE = True
CITY_ID = 524901  # 'Moscow,RU'
WEATHER_TIME_UPDATE = 'обновлено %s мин назад'
CONVERT_HPA_MMHG = 0.7506

# Датчик движения SR602 (можно настроить)
SENSOR_SR602_PIN = 13  # GPIO2_D4
SLEEP_ACTION = True  # Работа с датчиком движения, уход в сон и пробуждение
DELAY_OFF = 20  # Время ожидания без движения

# Высоковольтное реле (можно настроить)
RELAY_PIN = 4  # GPIO4_A4
BACKLIGHT_ACTION = True  # Работа с подсветкой, отключение/включения подстветки для исключения выгорания дисплея

# Энкодер KY040 (можно настроить)
BUTTON_KY040_PIN = 11  # SPI4_TXD
ROTATE_KY040_PIN = 12  # SPI4_RXD
CLK_KY040_PIN = 14  # SPI4_CLK

# Адреса i2c датчиков (можно настроить)
BMP280_ADDRESS = 0x77
AHT20_ADDRESS = 0x38
ADS1115_ADDRESS = 0x48


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
    timer_fixed_update = None
    timer_minute_fixed_update = None
    timer_weather = None
    screen_width = 0
    screen_height = 0

    def __init__(self, app_object: QApplication):
        super().__init__()
        screen = app_object.primaryScreen()
        size = screen.size()

        self.ui = ui_window.Ui_Form()
        self.ui.setupUi(self)
        self.setWindowIcon(QtGui.QIcon('%s/icon.ico' % WORK_DIR))

        if not RELEASE_PROD:
            self.multi_log('ПО панели в режиме разработки!')

        if RELEASE_PROD:
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
                              chg_callback=self.encoder_chg, sw_callback=self.encoder_button,
                              sw_debounce_time=100)

            self.ky040_thread = threading.Thread(target=encoder.watch)
            self.ky040_thread.start()

        self.calculation_size(size)

        # Добавляем красивость в виде тени на UI элементы
        for element in [self.ui.weather_container, self.ui.debug_container]:
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(16)
            shadow.setColor(QColor(0, 0, 0, 128))
            shadow.setXOffset(8)
            shadow.setYOffset(8)
            element.setGraphicsEffect(shadow)

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

    def encoder_inc(self, pos):
        """
        Callback метод вращения энкодера KY-040 по часовой стрелке
        :param pos: 0-100 позиция высчитанного положения
        """
        self.multi_log('Rotary incremented: %s' % pos)

    def encoder_dec(self, pos):
        """
        Callback метод вращения энкодера KY-040 против часовой стрелке
        :param pos: 0-100 позиция высчитанного положения
        """
        self.multi_log('Rotary decremented: %s' % pos)

    def encoder_chg(self, pos):
        """
        Callback метод измения угловой позиции энкодера KY-040
        :param pos: 0-100 позиция высчитанного вращения
        """
        self.multi_log('Rotary changed: %s' % pos)

    def encoder_button(self):
        """
        Callback метод нажатия на энкодер KY-040
        """
        self.multi_log("Pressed")

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
        self.ui.date_widget_hide.setStyleSheet(
            self.ui.date_widget_hide.styleSheet() + "font-size: %spx;" % self.fix(20))
        self.ui.time_widget.setStyleSheet(self.ui.time_widget.styleSheet() + "font-size: %spx;" % self.fix(55))
        self.ui.time_widget_hide.setStyleSheet(
            self.ui.time_widget_hide.styleSheet() + "font-size: %spx;" % self.fix(55))
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
        self.timer_weather.timeout.connect(self.update_weather)
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
        self.weather_update_timestamp += 1
        self.ui.weather_time_update_text.setText(WEATHER_TIME_UPDATE % self.weather_update_timestamp)
        self.update_met_sensor()

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
        self.ui.time_widget_hide.setText(date_time_display[0])
        self.ui.date_widget.setText(date_time_display[1])
        self.ui.date_widget_hide.setText(date_time_display[1])

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
