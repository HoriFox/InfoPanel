import time
import cv2
import imutils
import pickle
from transliterate import translit
import face_recognition
from imutils.video import VideoStream
from PyQt5.QtGui import QImage
from PyQt5.QtCore import QThread, Qt, pyqtSignal


class CameraThread(QThread):
    current_name = "Unknown"
    pause = False
    changePixmap = pyqtSignal(QImage)

    def __init__(self, mv, pause, encodingsP, cascade):
        super().__init__()
        self.mv = mv
        self.pause = pause
        self.data = pickle.load(open(encodingsP, "rb"), encoding="latin1")
        self.detector = cv2.CascadeClassifier(cascade)
        self.vs = VideoStream(usePiCamera=True).start()
        time.sleep(2.0)

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
                        if self.current_name != name:
                            self.current_name = name
                            self.mv.change_person(self.current_name)
                    names.append(name)

                for ((top, right, bottom, left), name) in zip(boxes, names):
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 225), 2)
                    y = top - 15 if top - 15 > 15 else top + 15
                    name_translit = translit(name, "ru", reversed=True)
                    cv2.putText(frame, name_translit, (left, y), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 255, 255), 2)

                rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgbImage.shape
                bytesPerLine = ch * w
                convertToQtFormat = QImage(rgbImage.data, w, h, bytesPerLine, QImage.Format_RGB888)
                #convertToQtFormat.setStyleSheet("border-bottom-left-radius: 10px;")
                # maybe this?
                #image = qimage2ndarray.array2qimage(frame)
                p = convertToQtFormat.scaled(450, 350, Qt.KeepAspectRatio)	
                
                self.changePixmap.emit(p)
                
            time.sleep(0.5)