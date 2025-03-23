import sys
import multiprocessing
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, QMessageBox
from spleeter.separator import Separator


class SpleeterGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.separator = Separator('spleeter:2stems')
        self.audio_file = None
        self.output_dir = None

    def init_ui(self):
        self.setWindowTitle('Spleeter GUI - Audio Stem Separator')
        self.setGeometry(100, 100, 400, 200)

        layout = QVBoxLayout()

        self.label = QLabel('Select an audio file and output directory to separate vocals and accompaniment.', self)
        layout.addWidget(self.label)

        self.select_audio_button = QPushButton('Select Audio File', self)
        self.select_audio_button.clicked.connect(self.open_file_dialog)
        layout.addWidget(self.select_audio_button)

        self.select_output_button = QPushButton('Select Output Directory', self)
        self.select_output_button.clicked.connect(self.open_output_dialog)
        layout.addWidget(self.select_output_button)

        self.process_button = QPushButton('Separate Stems', self)
        self.process_button.clicked.connect(self.separate_audio)
        self.process_button.setEnabled(False)
        layout.addWidget(self.process_button)

        self.setLayout(layout)

    def open_file_dialog(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Audio File", "", "Audio Files (*.mp3 *.wav *.flac)", options=options)
        if file_path:
            self.audio_file = file_path
            self.label.setText(f'Selected File: {file_path}')
            self.check_ready_to_process()

    def open_output_dialog(self):
        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if output_dir:
            self.output_dir = output_dir
            self.label.setText(f'Output Directory: {output_dir}')
            self.check_ready_to_process()

    def check_ready_to_process(self):
        if self.audio_file and self.output_dir:
            self.process_button.setEnabled(True)

    def separate_audio(self):
        try:
            self.separator.separate_to_file(self.audio_file, self.output_dir)
            QMessageBox.information(self, "Success", "Audio separation completed successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")


if __name__ == "__main__":
    multiprocessing.set_start_method('spawn')
    app = QApplication(sys.argv)
    window = SpleeterGUI()
    window.show()
    sys.exit(app.exec_())
