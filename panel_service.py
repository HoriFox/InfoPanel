#!/usr/bin/python
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QGraphicsOpacityEffect
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import QPixmap, QFont, QMovie
from PyQt5.QtCore import QTimer, QTime, Qt
from PyQt5.QtWebEngineWidgets import QWebEngineView


class MainWindow(QWidget):

    def __init__(self, screen):
        super().__init__()
        size = screen.size()
        screen_width = size.width()
        screen_height = size.height()
        #screen_width = 388
        #screen_height = 690
        dev_screen_width = 388
        dev_screen_height = 690
        coef_width = screen_width / dev_screen_width
        coef_height = screen_height / dev_screen_height
        print(coef_width, coef_height)
        self.setWindowFlag(Qt.FramelessWindowHint)
        #self.showMaximized()
        
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
        time_widget = QLabel("19:20")
        time_widget.setStyleSheet("font-size:{}px;color:#bdbdbd;".format(round(40 * coef_width)))
        hb_time.addWidget(time_widget)
        date_widget = QLabel("04.07.21")
        date_widget.setStyleSheet("font-size:{}px;color:#bdbdbd;margin-top:{}px;".format(round(20 * coef_width), round(6 * coef_width)))
        hb_time.addWidget(date_widget)
        hb_time.setAlignment(date_widget, Qt.AlignTop)
        hb_time.addStretch()
        vertical_l.addLayout(hb_time)
        
        vert_inner_h = QHBoxLayout()
        panel1_widget = QLabel("Panel1")
        panel1_widget.setStyleSheet("background-color: #e1e9fd;border-radius:4px;font-size:15px;color:#2f2f2f;padding:10px;")
        panel1_widget.setText("Multiline\ntext")
        vert_inner_h.addWidget(panel1_widget)
        panel2_widget = QLabel("Panel2")
        panel2_widget.setStyleSheet("background-color: #e1e9fd;border-radius:4px;font-size:15px;color:#2f2f2f;padding:10px;")
        vert_inner_h.addWidget(panel2_widget)
        vertical_l.addLayout(vert_inner_h)
        
        vert_inner_h2 = QHBoxLayout()
        panel3_widget = QLabel("Panel3")
        panel3_widget.setStyleSheet("background-color: #e1e9fd;border-radius:4px;font-size:15px;color:#2f2f2f;padding:10px;")
        op=QGraphicsOpacityEffect(self)
        op.setOpacity(0.60)
        panel3_widget.setGraphicsEffect(op)
        panel3_widget.setText("Full line block\nAnd some line\nYet and yet\n0.6 opacity")
        vert_inner_h2.addWidget(panel3_widget)
        vertical_l.addLayout(vert_inner_h2)
        
        vert_inner_h3 = QHBoxLayout()
        panel4_widget = QLabel("Panel3")
        panel4_widget.setStyleSheet("background-color: #e1e9fd;border-radius:4px;font-size:15px;color:#2f2f2f;padding:10px;")
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
        #panel5_widget.setStyleSheet("background-color: #e1e9fd;border-radius:4px;")
        panel5_widget.setMovie(movie)
        movie.start()
        vert_inner_h4.addWidget(panel5_widget)
        vertical_l.addLayout(vert_inner_h4)
        
        view = QWebEngineView()
        view.show()
        url = 'https://ru.stackoverflow.com/a/864975/201445'
        view.load(QUrl(url))
        
        vertical_l.addStretch()
        
        self.setLayout(vertical_l)
        
        print('w', screen_width, 'h', screen_height)
        self.resize(screen_width, screen_height)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    screen = app.primaryScreen()
    window = MainWindow(screen)
    window.show()

    sys.exit(app.exec_())
