#!/bin/python3

import sys
import platform
import requests
import json
import logging
import random
import pathlib
from subprocess import call, Popen, PIPE
from gpiozero import MotionSensor
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, 
QHBoxLayout, QGridLayout, QPushButton, QGraphicsOpacityEffect, QGraphicsDropShadowEffect)
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import QPixmap, QFont, QMovie, QImage, QPainter, QPainterPath
from PyQt5.QtCore import QTimer, QTime, Qt, QUrl, QDateTime, pyqtSlot
from newsapi import NewsApiClient
#from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
#from PyQt5.QtMultimediaWidgets import QVideoWidget
from mysqlhelper import DBConnection
from snn_service import CameraThread
from lib.access import WEATHER_API_KEY, NEWS_API_KEY

LOGLEVEL = logging.DEBUG
LOGFILE = '/var/log/infopanel.log'

logFormatter = logging.Formatter("[%(asctime)s] [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
log = logging.getLogger()
log.setLevel(LOGLEVEL)
fileHandler = logging.FileHandler(LOGFILE)
fileHandler.setFormatter(logFormatter)
log.addHandler(fileHandler)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
log.addHandler(consoleHandler)

BLOCK_TIME_UPDATE = 'последнее обновление в %s'

WORK_DIR = pathlib.Path(__file__).parent.resolve()

encodingsP = "%s/lib/snn/encodings.pickle" % WORK_DIR
cascade = "%s/lib/snn/haarcascade_frontalface_default.xml"  % WORK_DIR

RELEASE_PROD='5.10.17-v7l+'
#CITY_NAME='Moscow,RU'
CITY_ID=524901 #'Moscow,RU'
MOTION_SENSOR_PIN = 21


class MainWindow(QWidget):
    dev_screen_width = 388
    dev_screen_height = 690
    delay_on_tv = 20
    snn_work = True
    debug_news = False

    #Tech
    timeout_on_tv = 0
    time_hibernation = 0
    target_person = "Unknown"

    def __init__(self, screen):
            super().__init__()
            self.setWindowIcon(QtGui.QIcon('%s/icon.ico' % WORK_DIR))
            self.media_res = []
            self.pir_sensor = MotionSensor(MOTION_SENSOR_PIN)
            self.newsapi = NewsApiClient(api_key=NEWS_API_KEY)

            log.debug('Get status power tv')
            # Get current power status tv
            status_tv = Popen('echo pow 0 | cec-client -s -d 1 | grep "standby"', shell=True, stdout=PIPE)
            self.power_tv = True if len(status_tv.stdout.read()) == 0 else False
            if self.power_tv:
                    self.timeout_on_tv = self.delay_on_tv
            log.info('Current power status tv: %s' % ('on' if self.power_tv else 'off'))
            if self.snn_work:
                log.debug('Init camera/cv2/thread [> 2 sec]')
                self.camera_th = CameraThread(self, not self.power_tv, encodingsP, cascade)
            self.calculation_size(screen)
            self.init_timers()
            self.init_background()
            self.arrangement_content()
            
            #special update
            self.update_weather()
            self.update_news()


    def calculation_size(self, screen):
            """
            Method auto rescale windows size and calc coefficient
            """
            size = screen.size()
            if platform.release() == RELEASE_PROD:
                    self.screen_width = size.width()
                    self.screen_height = size.height()
            else:
                    self.screen_width = 388
                    self.screen_height = 690
            self.coef_width = self.screen_width / self.dev_screen_width
            self.coef_height = self.screen_height / self.dev_screen_height
            self.setWindowFlag(Qt.FramelessWindowHint)
            #self.showMaximized()
            log.debug('Window coefficients - c_width: %s, c_height: %s' % (round(self.coef_width, 3), round(self.coef_height, 3)))
            log.debug('Window size - width: %s, height: %s' % (self.screen_width, self.screen_height))
            self.resize(self.screen_width, self.screen_height)
		
		
    def init_timers(self):
            # Tech timer
            self.timer_fixed_update = QTimer()
            self.timer_fixed_update.setInterval(1000) # 1 sec
            self.timer_fixed_update.timeout.connect(self.fixed_update)
            self.timer_fixed_update.start()
            
            #self.timers = []
            #timer_weather = QTimer()
            #timer_weather.setInterval(30 * 60 * 1000) # 30 min
            #timer_weather.timeout.connect(self.update_weather)
            #timer_weather.start()
            #self.timers['timer_weather'] = timer_weather
        
        
    def init_background(self):
        label = QLabel(self)
        pixmap = QPixmap('%s/res/img/back_v3.png' % WORK_DIR)
        pixmap = pixmap.scaled(self.screen_width, self.screen_height, QtCore.Qt.KeepAspectRatio)
        label.setPixmap(pixmap)
        label.resize(self.screen_width, self.screen_height)


    @pyqtSlot(QImage)
    def setImage(self, image):
        # target = QPixmap()  
        # target.fill(Qt.transparent)
        # painter = QPainter(target)
        # path = QPainterPath()
        # path.addRoundedRect(0, 0, 450, 350, 25, 25)
        # painter.setClipPath(path)
        # painter.drawPixmap(0, 0, QPixmap.fromImage(image))
        self.cam_widget.setPixmap(QPixmap.fromImage(image))


    def arrangement_content(self):
        # >>> time/date panel
        vertical_l = QVBoxLayout()

        hb_time = QHBoxLayout()
        self.time_widget = QLabel('ВРЕМЯ')
        self.time_widget.setStyleSheet(
            "font-size:%sPX;color:#eaf0ff;" 
            % self.fix(35))
        hb_time.addWidget(self.time_widget)
        self.date_widget = QLabel('ДАТА/ДЕНЬ НЕДЕЛИ')
        self.date_widget.setStyleSheet(
            "font-size:%sPX;color:#eaf0ff;margin-top:%sPX;" 
            % self.fix([15, 6]))
        hb_time.addWidget(self.date_widget)
        hb_time.setAlignment(self.date_widget, Qt.AlignTop)
        hb_time.addStretch()
        vertical_l.addLayout(hb_time)
        # <<< time/date panel


        # >>> weather panel
        weather_layout = QGridLayout()
        back_weather_widget = QLabel()
        back_weather_widget.setStyleSheet(
            "background-color: rgba(188, 193, 206, 120);border-radius:%sPX;" 
            % self.fix(4))

        weather_content_v = QVBoxLayout()
        weather_content_h = QHBoxLayout()
        self.weather_img = QLabel()
        weather_content_h.addWidget(self.weather_img)
        self.weather_text = QLabel("обновление...")
        self.weather_text.setStyleSheet(
            "font-size:%sPX;color:#eaf0ff;" 
            % self.fix(14))
        weather_content_h.addWidget(self.weather_text)
        weather_content_h.addStretch()
        weather_content_v.addLayout(weather_content_h)

        self.weather_time_update_text = QLabel("время последнего обновления погоды")
        self.weather_time_update_text.setStyleSheet(
            "font-size:%sPX;color:#eaf0ff;padding:0 0 %sPX %sPX;" 
            % self.fix([8, 10, 10]))
        weather_content_v.addWidget(self.weather_time_update_text)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        back_weather_widget.setGraphicsEffect(shadow)

        weather_layout.addWidget(back_weather_widget, 0, 0)
        weather_layout.addLayout(weather_content_v, 0, 0)
        vertical_l.addLayout(weather_layout)
        # <<< weather panel


        # >>> news panel
        news_layout = QGridLayout()
        back_news_widget = QLabel()
        back_news_widget.setStyleSheet(
            "background-color: rgba(225, 233, 253, 120);border-radius:%sPX;" 
            % self.fix(4))

        news_content_v = QVBoxLayout()
        self.news_widget = QLabel("панель новостей")
        self.news_widget.setStyleSheet(
            "font-size:%sPX;color:#eaf0ff;padding:%sPX;" 
            % self.fix([12, 10]))
        self.news_widget.setWordWrap(True)
        news_content_v.addWidget(self.news_widget)

        self.news_time_update_text = QLabel("время последнего обновления новостей")
        self.news_time_update_text.setStyleSheet(
            "font-size:%sPX;color:#eaf0ff;padding:0 0 %sPX %sPX;" 
            % self.fix([8, 10, 10]))
        news_content_v.addWidget(self.news_time_update_text)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        back_news_widget.setGraphicsEffect(shadow)

        news_layout.addWidget(back_news_widget, 0, 0)
        news_layout.addLayout(news_content_v, 0, 0)
        vertical_l.addLayout(news_layout)
        # <<< news panel


        # >>> cam and todo list panel
        cam_todo_content_h = QHBoxLayout()

        self.cam_widget = QLabel("панель камеры")
        self.cam_widget.setStyleSheet(
            "background-color: rgba(225, 233, 253, 120);border-radius:%sPX;font-size:%sPX;color:#eaf0ff;padding:%sPX;" 
            % self.fix([4, 12, 10]))
        if self.snn_work:
            self.camera_th.changePixmap.connect(self.setImage)
            self.camera_th.start()
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        self.cam_widget.setGraphicsEffect(shadow)
        cam_todo_content_h.addWidget(self.cam_widget)

        self.what_buy_widget = QLabel("панель заметок")
        self.what_buy_widget.setStyleSheet(
            "background-color: rgba(225, 233, 253, 120);border-radius:%sPX;font-size:%sPX;color:#eaf0ff;padding:%sPX;" 
            % self.fix([4, 12, 10]))
        self.what_buy_widget.setWordWrap(True)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        self.what_buy_widget.setGraphicsEffect(shadow)
        cam_todo_content_h.addWidget(self.what_buy_widget)

        vertical_l.addLayout(cam_todo_content_h)
		# <<< cam and todo list panel
            
        
        # >>> 1 panel in line | opacity
        #vert_inner_h2 = QHBoxLayout()
        #panel3_widget = QLabel("Panel3")
        #panel3_widget.setStyleSheet(
        #	"background-color: #e1e9fd;border-radius:%sPX;font-size:%sPX;color:#2f2f2f;padding:%sPX;" 
        #	% self.fix([4, 15, 10]))
        # op=QGraphicsOpacityEffect(self)
        # op.setOpacity(0.60)
        # panel3_widget.setGraphicsEffect(op)
        #panel3_widget.setText("Full line block\nAnd some line\nYet and yet\n0.6 opacity")
        #vert_inner_h2.addWidget(panel3_widget)
        #vertical_l.addLayout(vert_inner_h2)
        # <<< 1 panel in line | opacity


        # >>> 1 gif image
        # layout_h = QHBoxLayout()
        # git_image_widget = QLabel()
        # gif_movie = QMovie("res/gif/giphy.gif")
        # gif_movie.setScaledSize(QtCore.QSize(self.screen_width*0.3-30, self.screen_width*0.3-30))
        # git_image_widget.setMovie(gif_movie)
        # if self.power_tv:
        #     gif_movie.start()
        # self.media_res.append(gif_movie)
        # layout_h.addWidget(git_image_widget)
        # vertical_l.addLayout(layout_h)
        # <<< 1 gif image


        vertical_l.addStretch()
        

        # >>> debug panel
        layout_h = QHBoxLayout()
        self.debug_widget = QLabel("строка отладки")
        self.debug_widget.setStyleSheet(
            "background-color: rgba(225, 233, 253, 120);border-radius:%sPX;font-size:%sPX;color:#eaf0ff;padding:%sPX;" 
            % self.fix([4, 7, 10]))
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        self.debug_widget.setGraphicsEffect(shadow)
        layout_h.addWidget(self.debug_widget)
        vertical_l.addLayout(layout_h)
        # <<< debug panel

        # <<<
        self.setLayout(vertical_l)


    def multi_log(self, *message):
            print_mes = ' '.join(map(str, message))
            log.debug(print_mes)
            self.debug_widget.setText(print_mes)


    def fixed_update(self):
            """
            Method of constant fixed update every 1 second
            """
            sensor_value = self.pir_sensor.motion_detected
            #self.multi_log('[DEBUG] Sensor:', sensor_value)
            if self.power_tv:
                    if not sensor_value:
                            if self.timeout_on_tv != 0:
                                    self.timeout_on_tv -= 1
                                    self.multi_log('[DEBUG]', self.timeout_on_tv)
                            else:
                                    self.hibernation()
                                    self.power_tv = False
                    else:
                            self.multi_log('[DEBUG] Motion found. Set delay')
                            self.timeout_on_tv = self.delay_on_tv
            else:
                    if sensor_value:
                            self.awake()
                            self.power_tv = True
                            self.timeout_on_tv = self.delay_on_tv
                
            # Update block
            if not self.power_tv:
                self.time_hibernation += 1
                return
                
            self.update_date_time()


    def hibernation(self):
            """
            Method switch the panel to hibernation
            """
            self.multi_log('Turn off panel')
            call("echo standby 0 | cec-client -s -d 1 > /dev/null", shell=True)
            self.time_hibernation = 0
            
            #Stop all UI update
            for item in self.media_res:
                item.stop()
        
            self.camera_th.set_pause()


    def awake(self):
            """
            Method switch the panel to awake
            """
            self.multi_log('Turn on panel')
            call("echo on 0 | cec-client -s -d 1 > /dev/null", shell=True)
            
            # 5 min update weather
            # Bad implementation
            # In this case, if you constantly walk nearby
            # before the counter becomes more than 5 minutes,
            # then there will be no update
            if self.time_hibernation >= 60 * 5:
                self.update_weather()
                self.update_news()

                
            #Start all UI update
            for item in self.media_res:
                item.start()
        
            self.camera_th.set_resume()


    def change_person(self, current_name):
        self.target_person = current_name
        self.update_todo_list()


    def update_date_time(self):
            """
            Method update date and time label
            """
            time = QDateTime.currentDateTime()
            date_time_display = time.toString('hh:mm:ss|dd.MM.yyyy dddd').split('|')
            self.time_widget.setText(date_time_display[0])
            self.date_widget.setText(date_time_display[1])


    def update_weather(self):
            """
            Method update weather label
            """
            self.multi_log('Weather updated')
            try:
                    if self.debug_news:
                        with open('stat.txt', encoding='utf-8', errors='ignore') as stat:
                            content = stat.read().replace('\'', '\"')
                            data = json.loads(content)
                    else:
                        res = requests.get("http://api.openweathermap.org/data/2.5/weather",
                            params={'id': CITY_ID, 'units': 'metric', 'lang': 'ru', 'APPID': WEATHER_API_KEY})
                        if res != None:
                            data = res.json()
                    if data != None:
                        pixmap = QPixmap('%s/res/img/weather_pack/%s.png' % (WORK_DIR, data['weather'][0]['icon']))
                        pixmap = pixmap.scaled(self.fix(50), self.fix(50), QtCore.Qt.KeepAspectRatio)
                        self.weather_img.setPixmap(pixmap)

                        self.weather_text.setText('%s\n%s...%s...%s' % (data['weather'][0]['description'], 
                                                    round(data['main']['temp_min']), 
                                                    round(data['main']['temp']), 
                                                    round(data['main']['temp_max'])))
                
                        time = QDateTime.currentDateTime()
                        date_time_display = time.toString('hh:mm:ss')
                        self.weather_time_update_text.setText(BLOCK_TIME_UPDATE % date_time_display)
            except Exception as e:
                    self.multi_log("[ERROR] Exception (find):", e)


    def update_news(self):
            max_index = 5
            """
            Method update news label
            """
            self.multi_log('News updated')
            try:
                top_headlines = self.newsapi.get_top_headlines(language='ru')
            except Exception as ex:
                self.multi_log('[WARNING] Error update news:', ex)
                return
		
            if top_headlines['status'] == 'ok':
                total = min(len(top_headlines['articles']), max_index)
                log.debug('Total news: %s' % total)
                index_new = random.randint(0, total - 1)
                log.debug('Current news: %s' % index_new)
                news_block = top_headlines['articles'][index_new]
                #date_time_public = news_block['publishedAt'].replace('Z', '').split('T')
                #title_show_block = news_block['source']['name'] + ' - ' + date_time_public[0] + ' в ' 
                #+ date_time_public[1] + '\n'
                # news_show_message = title_show_block + news_block['title'] + '\n' + news_block['description']
                if news_block['title'] == None or news_block['description'] == None:
                    log.warning('Title or description is None')
                    self.news_time_update_text.setText("сервис новостей сейчас отдыхает")
                else:
                    self.news_widget.setText('<b>' + news_block['title'] + '</b><br>' + news_block['description'])

                    time = QDateTime.currentDateTime()
                    date_time_display = time.toString('hh:mm:ss')
                    self.news_time_update_text.setText(BLOCK_TIME_UPDATE % date_time_display)
            else:
                self.news_widget.setText('при загрузке новостей произошла ошибка')


    def update_todo_list(self):
            """
            Method update todo label
            """
            self.multi_log('Todo updated by person')

            output_string = '%s, Вы ещё не создавали заметки...' % self.target_person

            link_bd = DBConnection(log, 
                                   user="dacrover_user",
                                   password="dacrover_pass",
                                   host="itsuki.e",
                                   port=3306,
                                   database= "dacrover")

            reminder_target = link_bd.select('reminders', where="`ReminderUser` = '" + self.target_person + "'", json=True)
            if (reminder_target != None and len(reminder_target) > 0):
                reminder_target = reminder_target[0]

                discReminder = reminder_target['ReminderDisc']
                listReminder = reminder_target['ReminderList'].split('[DEL]')

                output_string = '%s, напоминание для Вас:\n%s\n' % (self.target_person, discReminder) + '-'*30 + '\n\n' + '\n'.join(listReminder)

            self.what_buy_widget.setText(output_string)


    def fix(self, size, side='w'):
            """
            Method size adjustment to target platform
            size - var to adjustment
            side = {w, h} - side to use for adjustment
            """
            if type(size) == list:
                    return tuple(map(lambda x: round(x * self.coef_width if side=='w' else self.coef_height), size))
            else:
                    return round(size * self.coef_width if side=='w' else self.coef_height)


if __name__ == '__main__':
        app = QApplication(sys.argv)
        screen = app.primaryScreen()
        window = MainWindow(screen)
        window.show()

        sys.exit(app.exec_())
