#!/usr/bin/python
import sys
import platform
import requests
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QGraphicsOpacityEffect
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import QPixmap, QFont, QMovie
from PyQt5.QtCore import QTimer, QTime, Qt, QUrl, QDateTime
#from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
#from PyQt5.QtMultimediaWidgets import QVideoWidget
from lib.access import WEATHER_API_KEY


RELEASE_PROD='5.10.17-v7l+'
CITY_NAME='Moscow,RU'
CITY_ID=524901 #'Moscow,RU'


class MainWindow(QWidget):

	dev_screen_width = 388
	dev_screen_height = 690
	
	def __init__(self, screen):
		super().__init__()
		self.setWindowIcon(QtGui.QIcon('icon.ico'))

		self.calculation_size(screen)
		self.init_timers()
		self.init_background()
		self.arrangement_content()
		
		#special update
		self.update_weather()
		
		
	def calculation_size(self, screen):
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
		print('[DEBUG] Window coefficients - c_width:', self.coef_width, 'c_height:', self.coef_height)
		print('[DEBUG] Window size - width:', self.screen_width, 'height:', self.screen_height)
		self.resize(self.screen_width, self.screen_height)
		
		
	def init_timers(self):
		self.timer_time_date = QTimer()
		self.timer_time_date.setInterval(1000) # 1 sec
		self.timer_time_date.timeout.connect(self.update_date_time)
		self.timer_time_date.start()
		self.timer_weather = QTimer()
		self.timer_weather.setInterval(60000) # 60 sec
		self.timer_weather.timeout.connect(self.update_weather)
		self.timer_weather.start()
		
		
	def init_background(self):
		label = QLabel(self)
		pixmap = QPixmap('res/img/back_v3.png')
		pixmap = pixmap.scaled(self.screen_width, self.screen_height, QtCore.Qt.KeepAspectRatio)
		label.setPixmap(pixmap)
		label.resize(self.screen_width, self.screen_height)
		#label.setScaledContents(True)


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
		pixmap = QPixmap('res/img/weather_pack/10d.png')
		pixmap = pixmap.scaled(self.fix(100), self.fix(100), QtCore.Qt.KeepAspectRatio)
		self.weather_img.setPixmap(pixmap)
		weather_content_v.addWidget(self.weather_img)
		self.weather_text = QLabel("update...")
		self.weather_text.setStyleSheet(
			"font-size:%sPX;color:#eaf0ff;" 
			% self.fix(18))
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


		# >>> 1 gif image
		layout_h = QHBoxLayout()
		git_image_widget = QLabel()
		movie = QMovie("res/gif/giphy.gif")
		movie.setScaledSize(QtCore.QSize(self.screen_width*0.3-30, self.screen_width*0.3-30))
		git_image_widget.setMovie(movie)
		movie.start()
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

		# <<<
		self.setLayout(vertical_l)
	
        
	def update_date_time(self):
        	time = QDateTime.currentDateTime()
        	date_time_display = time.toString('hh:mm:ss|dd.MM.yyyy dddd').split('|')
        	self.time_widget.setText(date_time_display[0])
        	self.date_widget.setText(date_time_display[1])
        
        
	def update_weather(self):
		print('[INFO] Weather updated')
		try:
			#res = requests.get("http://api.openweathermap.org/data/2.5/weather",
			#	 params={'id': CITY_ID, 'units': 'metric', 'lang': 'ru', 'APPID': WEATHER_API_KEY})
			#data = res.json()

			# temporarily
			with open('stat.txt', encoding='utf-8', errors='ignore') as stat:
				content = stat.read().replace('\'', '\"')
				data = json.loads(content)

			pixmap = QPixmap('res/img/weather_pack/%s.png' % data['weather'][0]['icon'])
			pixmap = pixmap.scaled(self.fix(100), self.fix(100), QtCore.Qt.KeepAspectRatio)
			self.weather_img.setPixmap(pixmap)
			
			self.weather_text.setText('%s\n%s...%s...%s' % (data['weather'][0]['description'], 
								       round(data['main']['temp_min']), 
								       round(data['main']['temp']), 
								       round(data['main']['temp_max'])))
		except Exception as e:
			print("[ERROR] Exception (find):", e)
        
	def fix(self, size, side='w'):
		if type(size) == list:
			return tuple(map(lambda x: round(x * self.coef_width if side=='w' else self.coef_height), size))
		else:
			return round(size * self.coef_width if side=='w' else self.coef_height)
			
			
def get_weather_status():
	pass


if __name__ == '__main__':
	app = QApplication(sys.argv)
	screen = app.primaryScreen()
	window = MainWindow(screen)
	window.show()

	sys.exit(app.exec_())
