import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt
from subprocess import Popen


class StreamControl(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Yayın Kontrol Arayüzü")

        self.start_button = QPushButton("Yayını Başlat")
        self.start_button.clicked.connect(self.start_stream)
        self.start_button.setStyleSheet("font-size: 24px;")

        self.stop_button = QPushButton("Yayını Bitir")
        self.stop_button.clicked.connect(self.stop_stream)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("font-size: 24px;")

        self.status_label = QLabel("Yayın aktif değil")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 26px; color: red;")

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)

        main_layout = QVBoxLayout()
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.status_label)

        self.setLayout(main_layout)
        self.stream_process = None

    def start_stream(self):
        process = Popen(["ffmpeg/ffmpeg.exe", "-f", "gdigrab", "-s", "1920x1080", "-i", "desktop", "-r", "30", "-preset", "ultrafast", "-tune", "zerolatency", "-f", "rtsp", "rtsp://localhost:8554/1"])
        self.stream_process = process
        self.status_label.setText("Yayın aktif")
        self.status_label.setStyleSheet("font-size: 18px; color: green;")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop_stream(self):
        self.stream_process.terminate()
        self.stream_process.wait()
        self.status_label.setText("Yayın aktif değil")
        self.status_label.setStyleSheet("font-size: 18px; color: red;")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StreamControl()
    window.show()
    sys.exit(app.exec_())
