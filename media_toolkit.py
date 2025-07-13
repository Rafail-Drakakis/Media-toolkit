from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QTextEdit, QFileDialog, QLabel, QRadioButton,
    QButtonGroup, QMessageBox, QGroupBox, QComboBox
)
from urllib.error import URLError, HTTPError
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip 
from moviepy.video.compositing.CompositeVideoClip import concatenate_videoclips
from moviepy.audio.AudioClip import concatenate_audioclips 
from pydub import AudioSegment
from pydub.silence import split_on_silence
from punctuators.models import PunctCapSegModelONNX
import sys, os, glob, re, subprocess, json, http, speech_recognition

def numerical_sort(filename):
    return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', filename)]

def is_supported_file(file, extensions):
    return file.lower().endswith(tuple(extensions))

def merge_media(files, output_filename, media_type='video'):
    clips = []
    for file in files:
        if not is_supported_file(file, ['.mp4', '.mkv', '.avi'] if media_type=='video' else ['.mp3', '.wav']):
            continue
        clip = VideoFileClip(file) if media_type=='video' else AudioFileClip(file)
        clips.append(clip)
    if not clips:
        raise ValueError("No supported files to merge.")
    if media_type == 'video':
        final = concatenate_videoclips(clips, method='compose')
        final.write_videofile(output_filename)
    else:
        final = concatenate_audioclips(clips)
        final.write_audiofile(output_filename)
    return output_filename

def get_title(link):
    process = subprocess.Popen(['yt-dlp', '--get-title', link], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, _ = process.communicate()
    audio_title = stdout.decode().strip()
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', audio_title)
    return sanitized

def download_audio(link, audio_title):
    command = f'yt-dlp -x --audio-format mp3 -o "{audio_title}.%(ext)s" -f "bestaudio/best" {link}'
    subprocess.run(command, shell=True, check=True)

def download_video(link, video_title):
    command = f'yt-dlp -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" -o "{video_title}.%(ext)s" {link}'
    subprocess.run(command, shell=True, check=True)

def download_playlist(playlist_url):
    command = f"yt-dlp -J --flat-playlist {playlist_url}"
    output = subprocess.check_output(command, shell=True)
    data = json.loads(output)
    playlist_title = re.sub(r'[<>:"/\\|?*]', '_', data.get('title', 'playlist'))
    entries = data.get('entries', [])
    titles = [re.sub(r'[<>:"/\\|?*]', '_', e.get('title','')) for e in entries]
    urls = [e.get('url','') for e in entries]
    return playlist_title, titles, urls

def process_and_enhance_text(text):
    model = PunctCapSegModelONNX.from_pretrained("pcs_en")
    results = model.infer([text.lower()])
    enhanced = ''
    for output in results:
        for line in output:
            enhanced += line.replace('<unk>', ' ').replace('<Unk>', ' ') + '\n'
    return enhanced

def split_audio_file(input_file, max_duration_ms, silence_threshold=-50, min_silence_duration=80):
    audio = AudioSegment.from_file(input_file)
    if len(audio) <= max_duration_ms:
        return [input_file]
    segments = split_on_silence(audio, min_silence_len=min_silence_duration, silence_thresh=silence_threshold)
    parts = []
    base = os.path.splitext(input_file)[0]
    for i, segment in enumerate(segments, start=1):
        out_path = f"{base}_part{i}.wav"
        segment.export(out_path, format='wav')
        parts.append(out_path)
    os.remove(input_file)
    return parts

def recognize_audio(wav_path):
    rec = speech_recognition.Recognizer()
    with speech_recognition.AudioFile(wav_path) as src:
        audio_data = rec.record(src)
    os.remove(wav_path)
    try:
        return rec.recognize_google(audio_data)
    except:
        return ''

def merge_text_files(merged_name):
    files = [f for f in os.listdir() if f.endswith('.txt') and f != f'{merged_name}.txt']
    files = sorted(files, key=numerical_sort)
    with open(f'{merged_name}.txt', 'w') as out:
        for fname in files:
            out.write(f"// {fname}\n")
            with open(fname) as f:
                out.write(f.read() + '\n')
            os.remove(fname)
    return f'{merged_name}.txt'

def convert_audio_to_text(media_files):
    output_files = []
    for media in media_files:
        wav = os.path.splitext(media)[0] + '.wav'
        AudioFileClip(media).write_audiofile(wav, codec='pcm_s16le')
        parts = split_audio_file(wav, max_duration_ms=120*1000)
        recognized = ''
        for part in parts:
            recognized += recognize_audio(part) + '\n'
        if recognized.strip():
            enhanced = process_and_enhance_text(recognized)
            outname = os.path.splitext(media)[0] + '_enhanced.txt'
            with open(outname, 'w') as out:
                out.write(enhanced)
            output_files.append(outname)
    return output_files

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Media Tool GUI')
        self.resize(800, 600)

        tabs = QTabWidget()
        tabs.addTab(self.merge_tab_ui(), 'Merge Media')
        tabs.addTab(self.convert_tab_ui(), 'Convert Media')

        self.setCentralWidget(tabs)

    def merge_tab_ui(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # File selection
        file_layout = QHBoxLayout()
        self.file_list = []
        self.file_display = QTextEdit()
        self.file_display.setReadOnly(True)
        select_btn = QPushButton('Select Files')
        select_btn.clicked.connect(self.select_files)
        ext_btn = QPushButton('Scan by Extension')
        ext_btn.clicked.connect(self.scan_extension)
        file_layout.addWidget(select_btn)
        file_layout.addWidget(ext_btn)

        layout.addLayout(file_layout)
        layout.addWidget(QLabel('Selected files:'))
        layout.addWidget(self.file_display)

        # Media type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel('Media Type:'))
        self.video_radio = QRadioButton('Video')
        self.audio_radio = QRadioButton('Audio')
        self.video_radio.setChecked(True)
        type_layout.addWidget(self.video_radio)
        type_layout.addWidget(self.audio_radio)

        layout.addLayout(type_layout)

        # Output name
        out_layout = QHBoxLayout()
        out_layout.addWidget(QLabel('Output file:'))
        self.out_name = QLineEdit()
        out_layout.addWidget(self.out_name)
        layout.addLayout(out_layout)

        merge_btn = QPushButton('Merge')
        merge_btn.clicked.connect(self.merge_action)
        layout.addWidget(merge_btn)

        self.merge_log = QTextEdit()
        self.merge_log.setReadOnly(True)
        layout.addWidget(QLabel('Log:'))
        layout.addWidget(self.merge_log)

        tab.setLayout(layout)
        return tab

    def convert_tab_ui(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # Mode selection
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel('Mode:'))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(['URL to Text', 'Playlist to Text', 'Local Files to Text'])
        self.mode_combo.currentIndexChanged.connect(self.switch_mode)
        mode_layout.addWidget(self.mode_combo)
        layout.addLayout(mode_layout)

        # URL widgets
        self.url_widget = QWidget()
        url_layout = QVBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('Enter URL')
        url_layout.addWidget(self.url_input)
        url_radio_layout = QHBoxLayout()
        url_radio_layout.addWidget(QLabel('Download:'))
        self.url_video_radio = QRadioButton('Video')
        self.url_audio_radio = QRadioButton('Audio')
        self.url_audio_radio.setChecked(True)
        url_radio_layout.addWidget(self.url_video_radio)
        url_radio_layout.addWidget(self.url_audio_radio)
        url_layout.addLayout(url_radio_layout)
        self.url_widget.setLayout(url_layout)

        # Playlist widget (reuse same controls)
        self.playlist_widget = self.url_widget

        # Local files widget
        self.local_widget = QWidget()
        local_layout = QVBoxLayout()
        self.local_list = []
        self.local_display = QTextEdit()
        self.local_display.setReadOnly(True)
        local_btn = QPushButton('Select Local Media Files')
        local_btn.clicked.connect(self.select_local_files)
        local_layout.addWidget(local_btn)
        local_layout.addWidget(self.local_display)
        self.local_widget.setLayout(local_layout)

        layout.addWidget(self.url_widget)
        layout.addWidget(self.local_widget)
        self.local_widget.hide()

        convert_btn = QPushButton('Convert')
        convert_btn.clicked.connect(self.convert_action)
        layout.addWidget(convert_btn)

        self.convert_log = QTextEdit()
        self.convert_log.setReadOnly(True)
        layout.addWidget(QLabel('Log:'))
        layout.addWidget(self.convert_log)

        tab.setLayout(layout)
        return tab

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'Select Media Files')
        if files:
            self.file_list = files
            self.file_display.setPlainText("\n".join(files))

    def scan_extension(self):
        ext, ok = QFileDialog.getSaveFileName(self, 'Specify Extension', filter='*.ext')
        if ok:
            _, extension = os.path.splitext(ext)
            files = glob.glob(os.path.join(os.getcwd(), f'*{extension}'))
            self.file_list = files
            self.file_display.setPlainText("\n".join(files))

    def merge_action(self):
        if not self.file_list:
            QMessageBox.warning(self, 'Warning', 'No files selected')
            return
        out = self.out_name.text().strip()
        if not out:
            QMessageBox.warning(self, 'Warning', 'Specify output filename')
            return
        mtype = 'video' if self.video_radio.isChecked() else 'audio'
        try:
            result = merge_media(self.file_list, out, media_type=mtype)
            self.merge_log.append(f'Merged into: {result}')
            QMessageBox.information(self, 'Success', f'Media merged into {result}')
        except Exception as e:
            self.merge_log.append(str(e))
            QMessageBox.critical(self, 'Error', str(e))

    def switch_mode(self, index):
        if index == 0:  # URL
            self.url_widget.show()
            self.local_widget.hide()
        elif index == 1:  # Playlist
            self.url_widget.show()
            self.local_widget.hide()
        else:  # Local
            self.url_widget.hide()
            self.local_widget.show()

    def select_local_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'Select Local Media Files')
        if files:
            self.local_list = files
            self.local_display.setPlainText("\n".join(files))

    def convert_action(self):
        mode = self.mode_combo.currentIndex()
        try:
            if mode == 0:  # URL
                link = self.url_input.text().strip()
                title = get_title(link)
                if self.url_video_radio.isChecked():
                    download_video(link, title)
                    media_files = [title + '.mp4']
                else:
                    download_audio(link, title)
                    media_files = [title + '.mp3']
                outs = convert_audio_to_text(media_files)

            elif mode == 1:  # Playlist
                link = self.url_input.text().strip()
                name, titles, urls = download_playlist(link)
                media_files = []
                if self.url_video_radio.isChecked():
                    for u, t in zip(urls, titles):
                        download_video(u, t)
                        media_files.append(t + '.mp4')
                else:
                    for u, t in zip(urls, titles):
                        download_audio(u, t)
                        media_files.append(t + '.mp3')
                outs = convert_audio_to_text(media_files)
                merge_text_files(name)
                outs.append(name + '.txt')

            else:  # Local
                if not self.local_list:
                    QMessageBox.warning(self, 'Warning', 'No local files selected')
                    return
                outs = convert_audio_to_text(self.local_list)
                if len(outs) > 1:
                    merged = merge_text_files('merged')
                    outs.append(merged)

            for f in outs:
                self.convert_log.append(f'Created: {f}')
            QMessageBox.information(self, 'Done', 'Conversion completed.')
        except Exception as e:
            self.convert_log.append(str(e))
            QMessageBox.critical(self, 'Error', str(e))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

