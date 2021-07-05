#!/usr/bin/python
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QGraphicsOpacityEffect
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import QPixmap, QFont, QMovie
from PyQt5.QtCore import QTimer, QTime, Qt, QUrl, QDateTime
#from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
#from PyQt5.QtMultimediaWidgets import QVideoWidget


class MainWindow(QWidget):

	dev_screen_width = 388
	dev_screen_height = 690

	def __init__(self, screen):
		super().__init__()
		size = screen.size()
		# Unlock to prod
		screen_width = size.width()
		screen_height = size.height()
		# Lock to prod
		#screen_width = 388
		#screen_height = 690
		self.coef_width = screen_width / self.dev_screen_width
		self.coef_height = screen_height / self.dev_screen_height
		print(self.coef_width, self.coef_height)
		self.setWindowFlag(Qt.FramelessWindowHint)
		#self.showMaximized()

		self.timer = QTimer()
		self.timer.timeout.connect(self.update_date_time)
		self.timer.start()

		# -- Back
		label = QLabel(self)
		pixmap = QPixmap('back_v3.png')
		pixmap = pixmap.scaled(screen_width, screen_height, QtCore.Qt.KeepAspectRatio)
		label.setPixmap(pixmap)
		label.resize(screen_width, screen_height)
		#label.setScaledContents(True)
		# -- Back

		vertical_l = QVBoxLayout()

		hb_time = QHBoxLayout()
		self.time_widget = QLabel()
		self.time_widget.setStyleSheet("font-size:%sPX;color:#bdbdbd;" % self.fix(35))
		hb_time.addWidget(self.time_widget)
		self.date_widget = QLabel()
		self.date_widget.setStyleSheet("font-size:%sPX;color:#bdbdbd;margin-top:%sPX;" % self.fix([15, 6]))
		hb_time.addWidget(self.date_widget)
		hb_time.setAlignment(self.date_widget, Qt.AlignTop)
		hb_time.addStretch()
		vertical_l.addLayout(hb_time)

		vert_inner_h = QHBoxLayout()
		panel1_widget = QLabel("Panel1")
		panel1_widget.setStyleSheet("background-color: #e1e9fd;border-radius:%sPX;font-size:%sPX;color:#2f2f2f;padding:%sPX;" % self.fix([4, 15, 10]))
		panel1_widget.setText("Multiline\ntext")
		vert_inner_h.addWidget(panel1_widget)
		panel2_widget = QLabel("Panel2")
		panel2_widget.setStyleSheet("background-color: #e1e9fd;border-radius:%sPX;font-size:%sPX;color:#2f2f2f;padding:%sPX;" % self.fix([4, 15, 10]))
		vert_inner_h.addWidget(panel2_widget)
		vertical_l.addLayout(vert_inner_h)

		vert_inner_h2 = QHBoxLayout()
		panel3_widget = QLabel("Panel3")
		panel3_widget.setStyleSheet("background-color: #e1e9fd;border-radius:%sPX;font-size:%sPX;color:#2f2f2f;padding:%sPX;" % self.fix([4, 15, 10]))
		op=QGraphicsOpacityEffect(self)
		op.setOpacity(0.60)
		panel3_widget.setGraphicsEffect(op)
		panel3_widget.setText("Full line block\nAnd some line\nYet and yet\n0.6 opacity")
		vert_inner_h2.addWidget(panel3_widget)
		vertical_l.addLayout(vert_inner_h2)

		vert_inner_h3 = QHBoxLayout()
		panel4_widget = QLabel("Panel3")
		panel4_widget.setStyleSheet("background-color: #e1e9fd;border-radius:%sPX;font-size:%sPX;color:#2f2f2f;padding:%sPX;" % self.fix([4, 15, 10]))
		op=QGraphicsOpacityEffect(self)
		op.setOpacity(0.30)
		panel4_widget.setGraphicsEffect(op)
		panel4_widget.setText("0.3 opacity")
		vert_inner_h3.addWidget(panel4_widget)
		vertical_l.addLayout(vert_inner_h3)

		vert_inner_h4 = QHBoxLayout()
		panel5_widget = QLabel()
		movie = QMovie("giphy.gif")
		movie.setScaledSize(QtCore.QSize(screen_width*0.3-30, screen_width*0.3-30))
		panel5_widget.setMovie(movie)
		movie.start()
		vert_inner_h4.addWidget(panel5_widget)
		vertical_l.addLayout(vert_inner_h4)

		#vert_inner_h5 = QHBoxLayout()
		#video_widget = QVideoWidget()
		#media_player = QMediaPlayer()
		#media_player.setVideoOutput(video_widget)
		#media_player.setMedia(QMediaContent(QUrl.fromLocalFile('video.mp4')))
		#media_player.play()
		#vert_inner_h5.addWidget(video_widget)
		#vertical_l.addLayout(vert_inner_h5)

		vertical_l.addStretch()

		self.setLayout(vertical_l)

		print('w', screen_width, 'h', screen_height)
		self.resize(screen_width, screen_height)
		
        
	def update_date_time(self):
        	time = QDateTime.currentDateTime()
        	date_time_display = time.toString('hh:mm:ss|dd.MM.yyyy dddd').split('|')
        	self.time_widget.setText(date_time_display[0])
        	self.date_widget.setText(date_time_display[1])
        
	def fix(self, size, side='w'):
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
