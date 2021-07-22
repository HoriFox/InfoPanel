#!/bin/python3

import sys
import platform
import requests
import json
from imutils.video import VideoStream
import face_recognition
import imutils
import pickle
import cv2
import time
from subprocess import call, Popen, PIPE
from picamera import PiCamera
from gpiozero import MotionSensor
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QGraphicsOpacityEffect
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import QPixmap, QFont, QMovie, QImage
from PyQt5.QtCore import QTimer, QTime, Qt, QUrl, QDateTime, QThread, pyqtSignal, pyqtSlot
#from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
#from PyQt5.QtMultimediaWidgets import QVideoWidget
from lib.access import WEATHER_API_KEY

encodingsP = "lib/snn/encodings.pickle"
cascade = "lib/snn/haarcascade_frontalface_default.xml"

RELEASE_PROD='5.10.17-v7l+'
#CITY_NAME='Moscow,RU'
CITY_ID=524901 #'Moscow,RU'
MOTION_SENSOR_PIN = 21


class Thread(QThread):
	currentname = "unknown"
	pause = False
	changePixmap = pyqtSignal(QImage)

	def __init__(self, pause, data, detector, vs):
	    super().__init__()
	    self.pause = pause
	    self.data = data
	    self.detector = detector
	    self.vs = vs 

	def set_pause(self):
	    self.pause = True
	    
	def set_resume(self):
	    self.pause = False

	def run(self):
		while True:
			if not self.pause:
			    frame = self.vs.read()
			    frame = imutils.resize(frame, width=500)
			
			    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
			    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

			    rects = self.detector.detectMultiScale(gray, scaleFactor=1.1, 
				    minNeighbors=5, minSize=(30, 30),
				    flags=cv2.CASCADE_SCALE_IMAGE)

			    boxes = [(y, x + w, y + h, x) for (x, y, w, h) in rects]

			    encodings = face_recognition.face_encodings(rgb, boxes)
			    names = []

			    for encoding in encodings:
				    matches = face_recognition.compare_faces(self.data["encodings"],
					    encoding)
				    name = "Unknown"

				    if True in matches:
					    matchedIdxs = [i for (i, b) in enumerate(matches) if b]
					    counts = {}

					    for i in matchedIdxs:
						    name = self.data["names"][i]
						    counts[name] = counts.get(name, 0) + 1

					    name = max(counts, key=counts.get)
			    
					    if self.currentname != name:
						    self.currentname = name
						    #print(self.currentname)

				    names.append(name)

			    for ((top, right, bottom, left), name) in zip(boxes, names):
				    cv2.rectangle(frame, (left, top), (right, bottom),
					    (0, 255, 225), 2)
				    y = top - 15 if top - 15 > 15 else top + 15
				    cv2.putText(frame, name, (left, y), cv2.FONT_HERSHEY_SIMPLEX,
					    .8, (0, 255, 255), 2)

			    rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
			    h, w, ch = rgbImage.shape
			    bytesPerLine = ch * w
			    convertToQtFormat = QImage(rgbImage.data, w, h, bytesPerLine, QImage.Format_RGB888)
			    # maybe this?
			    #image = qimage2ndarray.array2qimage(frame)
			    p = convertToQtFormat.scaled(640, 480, Qt.KeepAspectRatio)	
			    
			    self.changePixmap.emit(p)
			    
			time.sleep(1.0)
		

class MainWindow(QWidget):

	dev_screen_width = 388
	dev_screen_height = 690
	delay_on_tv = 10

	#Tech
	currentname = "unknown"
	timeout_on_tv = 0
	time_hibernation = 0


	def __init__(self, screen):
            super().__init__()
            self.setWindowIcon(QtGui.QIcon('icon.ico'))

            self.media_res = []

            self.data = pickle.load(open(encodingsP, "rb"), encoding="latin1")
            self.detector = cv2.CascadeClassifier(cascade)
            self.vs = VideoStream(usePiCamera=True).start()
            time.sleep(2.0)
	    
            self.pir_sensor = MotionSensor(MOTION_SENSOR_PIN)
            
            # Get current power status tv
            status_tv = Popen('echo pow 0 | cec-client -s -d 1 | grep "standby"', shell=True, stdout=PIPE)
            self.power_tv = True if len(status_tv.stdout.read()) == 0 else False
            if self.power_tv:
                    self.timeout_on_tv = self.delay_on_tv
            print('[INFO] Current power status tv:', 'on' if self.power_tv else 'off')

            self.calculation_size(screen)
            self.init_timers()
            self.init_background()
            self.arrangement_content()
            
                #special update
            self.update_weather()


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
            print('[DEBUG] Window coefficients - c_width:', round(self.coef_width, 3), ', c_height:', round(self.coef_height, 3))
            print('[DEBUG] Window size - width:', self.screen_width, ', height:', self.screen_height)
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
		pixmap = QPixmap('res/img/back_v3.png')
		pixmap = pixmap.scaled(self.screen_width, self.screen_height, QtCore.Qt.KeepAspectRatio)
		label.setPixmap(pixmap)
		label.resize(self.screen_width, self.screen_height)
		#label.setScaledContents(True)


	@pyqtSlot(QImage)
	def setImage(self, image):
	    self.cam_widget.setPixmap(QPixmap.fromImage(image))


	def arrangement_content(self):
		# >>>
		vertical_l = QVBoxLayout()

		hb_time = QHBoxLayout()
		self.time_widget = QLabel()
		self.time_widget.setStyleSheet(
			"font-size:%sPX;color:#eaf0ff;" 
			% self.fix(35))
		hb_time.addWidget(self.time_widget)
		self.date_widget = QLabel()
		self.date_widget.setStyleSheet(
			"font-size:%sPX;color:#eaf0ff;margin-top:%sPX;" 
			% self.fix([15, 6]))
		hb_time.addWidget(self.date_widget)
		hb_time.setAlignment(self.date_widget, Qt.AlignTop)
		hb_time.addStretch()
		vertical_l.addLayout(hb_time)


		# >>> weather panel
		weather_layout = QGridLayout()
		back_weather_widget = QLabel()
		back_weather_widget.setStyleSheet(
			"background-color: #bcc1ce;border-radius:%sPX;" 
			% self.fix(4))
		weather_content_v = QHBoxLayout()
		self.weather_img = QLabel()
		#pixmap = QPixmap('res/img/weather_pack/10d.png')
		#pixmap = pixmap.scaled(self.fix(100), self.fix(100), QtCore.Qt.KeepAspectRatio)
		#self.weather_img.setPixmap(pixmap)
		weather_content_v.addWidget(self.weather_img)
		self.weather_text = QLabel("update...")
		self.weather_text.setStyleSheet(
			"font-size:%sPX;color:#eaf0ff;" 
			% self.fix(14))
		weather_content_v.addWidget(self.weather_text)
		weather_content_v.addStretch()
		weather_layout.addWidget(back_weather_widget, 0, 0)
		weather_layout.addLayout(weather_content_v, 0, 0)
		vertical_l.addLayout(weather_layout)
		# <<< weather panel
		
		
		# >>> 1 panel in line
		layout_h = QHBoxLayout()
		what_buy_widget = QLabel("Panel3")
		what_buy_widget.setStyleSheet(
			"background-color: #e1e9fd;border-radius:%sPX;font-size:%sPX;color:#2f2f2f;padding:%sPX;" 
			% self.fix([4, 15, 10]))
		what_buy_widget.setText("Что купить? (тестовая)\n> Сыр\n> Молоко\n> Хлеб")
		layout_h.addWidget(what_buy_widget)
		vertical_l.addLayout(layout_h)
		# <<< 1 panel in line
		
		# >>> 1 panel in line
		layout_h = QHBoxLayout()
		self.cam_widget = QLabel("Camera panel")
		#self.cam_widget.resize(400, 300)
		self.cam_widget.setStyleSheet(
			"background-color: #e1e9fd;border-radius:%sPX;font-size:%sPX;color:#2f2f2f;padding:%sPX;" 
			% self.fix([4, 15, 10]))
		self.camera_th = Thread(not self.power_tv, self.data, self.detector, self.vs)
		self.camera_th.changePixmap.connect(self.setImage)
		self.camera_th.start()
		layout_h.addWidget(self.cam_widget)
		vertical_l.addLayout(layout_h)
		# <<< 1 panel in line
			
		
		# >>> 2 panel in line
		#vert_inner_h1 = QHBoxLayout()
		#panel1_widget = QLabel("Panel1")
		#panel1_widget.setStyleSheet(
		#	"background-color: #e1e9fd;border-radius:%sPX;font-size:%sPX;color:#2f2f2f;padding:%sPX;" 
		#	% self.fix([4, 15, 10]))
		#vert_inner_h1.addWidget(panel1_widget)
		#panel2_widget = QLabel("Panel2")
		#panel2_widget.setStyleSheet(
		#	"background-color: #e1e9fd;border-radius:%sPX;font-size:%sPX;color:#2f2f2f;padding:%sPX;" 
		#	% self.fix([4, 15, 10]))
		#vert_inner_h1.addWidget(panel2_widget)
		#vertical_l.addLayout(vert_inner_h1)
		# <<< 2 panel in line


		# >>> 1 panel in line | opacity
		#vert_inner_h2 = QHBoxLayout()
		#panel3_widget = QLabel("Panel3")
		#panel3_widget.setStyleSheet(
		#	"background-color: #e1e9fd;border-radius:%sPX;font-size:%sPX;color:#2f2f2f;padding:%sPX;" 
		#	% self.fix([4, 15, 10]))
		#op=QGraphicsOpacityEffect(self)
		#op.setOpacity(0.60)
		#panel3_widget.setGraphicsEffect(op)
		#panel3_widget.setText("Full line block\nAnd some line\nYet and yet\n0.6 opacity")
		#vert_inner_h2.addWidget(panel3_widget)
		#vertical_l.addLayout(vert_inner_h2)
		# <<< 1 panel in line | opacity


		# >>> 1 panel in line | opacity
		#vert_inner_h3 = QHBoxLayout()
		#panel4_widget = QLabel("Panel3")
		#panel4_widget.setStyleSheet(
		#	"background-color: #e1e9fd;border-radius:%sPX;font-size:%sPX;color:#2f2f2f;padding:%sPX;" 
		#	% self.fix([4, 15, 10]))
		#op=QGraphicsOpacityEffect(self)
		#op.setOpacity(0.30)
		#panel4_widget.setGraphicsEffect(op)
		#panel4_widget.setText("0.3 opacity")
		#vert_inner_h3.addWidget(panel4_widget)
		#vertical_l.addLayout(vert_inner_h3)
		# <<< 1 panel in line | opacity

		#layout_h = QHBoxLayout()
		#camera_preview_widget = QLabel()
		#pixmap = QPixmap('res/img/back_v3.png')
		#pixmap = pixmap.scaled(400, 300, QtCore.Qt.KeepAspectRatio)
		#camera_preview_widget.setPixmap(pixmap)
		#layout_h.addWidget(camera_preview_widget)
		#vertical_l.addLayout(layout_h)

		# >>> 1 gif image
		layout_h = QHBoxLayout()
		git_image_widget = QLabel()
		gif_movie = QMovie("res/gif/giphy.gif")
		gif_movie.setScaledSize(QtCore.QSize(self.screen_width*0.3-30, self.screen_width*0.3-30))
		git_image_widget.setMovie(gif_movie)
		if self.power_tv:
			gif_movie.start()
		self.media_res.append(gif_movie)
		layout_h.addWidget(git_image_widget)
		vertical_l.addLayout(layout_h)
		# <<< 1 gif image


		#vert_inner_h5 = QHBoxLayout()
		#video_widget = QVideoWidget()
		#media_player = QMediaPlayer()
		#media_player.setVideoOutput(video_widget)
		#media_player.setMedia(QMediaContent(QUrl.fromLocalFile('video.mp4')))
		#media_player.play()
		#vert_inner_h5.addWidget(video_widget)
		#vertical_l.addLayout(vert_inner_h5)

		vertical_l.addStretch()
		
		# >>> 1 panel in line
		layout_h = QHBoxLayout()
		self.debug_widget = QLabel("debug line")
		self.debug_widget.setStyleSheet(
			"background-color: #e1e9fd;border-radius:%sPX;font-size:%sPX;color:#2f2f2f;padding:%sPX;" 
			% self.fix([4, 7, 10]))
		layout_h.addWidget(self.debug_widget)
		vertical_l.addLayout(layout_h)
		# <<< 1 panel in line

		# <<<
		self.setLayout(vertical_l)


	def log(self, *message):
            print_mes = ' '.join(map(str, message))
            print(print_mes)
            self.debug_widget.setText(print_mes)


	def fixed_update(self):
            """
            Method of constant fixed update every 1 second
            """
            sensor_value = self.pir_sensor.motion_detected
            #self.log('[DEBUG] Sensor:', sensor_value)
            if self.power_tv:
                    if not sensor_value:
                            if self.timeout_on_tv != 0:
                                    self.timeout_on_tv -= 1
                                    self.log('[DEBUG]', self.timeout_on_tv)
                            else:
                                    self.hibernation()
                                    self.power_tv = False
                    else:
                            self.log('[DEBUG] Motion found. Set delay')
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
            self.log('[INFO] Turn off panel')
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
            self.log('[INFO] Turn on panel')
            call("echo on 0 | cec-client -s -d 1 > /dev/null", shell=True)
            
            # 5 min update weather
            # Bad implementation
            # In this case, if you constantly walk nearby
            # before the counter becomes more than 5 minutes,
            # then there will be no update
            if self.time_hibernation >= 60 * 5:
                self.update_weather
                
            #Start all UI update
            for item in self.media_res:
                item.start()
		
            self.camera_th.set_resume()
        
	
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
            self.log('[INFO] Weather updated')
            try:
                    #res = requests.get("http://api.openweathermap.org/data/2.5/weather",
                    #    params={'id': CITY_ID, 'units': 'metric', 'lang': 'ru', 'APPID': WEATHER_API_KEY})
                    #data = res.json()

                    # temporarily
                    with open('stat.txt', encoding='utf-8', errors='ignore') as stat:
                       content = stat.read().replace('\'', '\"')
                       data = json.loads(content)

                    pixmap = QPixmap('res/img/weather_pack/%s.png' % data['weather'][0]['icon'])
                    pixmap = pixmap.scaled(self.fix(50), self.fix(50), QtCore.Qt.KeepAspectRatio)
                    self.weather_img.setPixmap(pixmap)

                    self.weather_text.setText('%s\n%s...%s...%s' % (data['weather'][0]['description'], 
                                               round(data['main']['temp_min']), 
                                               round(data['main']['temp']), 
                                               round(data['main']['temp_max'])))
            except Exception as e:
                    self.log("[ERROR] Exception (find):", e)
        
        
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
