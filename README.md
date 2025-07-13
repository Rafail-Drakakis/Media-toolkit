# Media Toolkit

Media Toolkit is a desktop application for merging media files and converting audio to text. It provides a PyQt5-based GUI with two main features:

1. **Merge Media** – Combine multiple video or audio files into a single file.
2. **Convert Media** – Download media from the web or process local files and convert their audio tracks into text transcripts.

## Features

- Merge video (`.mp4`, `.mkv`, `.avi`) or audio (`.mp3`, `.wav`) files.
- Download single videos or entire playlists via `yt-dlp`.
- Convert downloaded or local media files into text using `speech_recognition`.
- Enhance transcripts with punctuation and capitalization via the `pcs_en` model from [`punctuators`](https://github.com/tag12/punctuators).
- Simple GUI built with PyQt5.

## Requirements

- Python 3.8+
- [PyQt5](https://pypi.org/project/PyQt5/)
- [moviepy](https://pypi.org/project/moviepy/)
- [pydub](https://pypi.org/project/pydub/)
- [speech_recognition](https://pypi.org/project/SpeechRecognition/)
- [yt-dlp](https://pypi.org/project/yt-dlp/)
- [punctuators](https://pypi.org/project/punctuators/) (for the `pcs_en` model)

Install the dependencies with pip:

```bash
pip install PyQt5 moviepy pydub SpeechRecognition yt-dlp punctuators
```

`yt-dlp` may also require [FFmpeg](https://ffmpeg.org/) to be installed on your system.

## Usage

Run the GUI application with:

```bash
python media_toolkit.py
```

### Merge Media

1. Use **Select Files** to choose media files or **Scan by Extension** to automatically gather files in the current directory.
2. Choose whether you are merging **Video** or **Audio** files.
3. Specify the output filename and click **Merge**.
4. Progress and messages are shown in the log box.

### Convert Media

1. Choose the mode:
   - **URL to Text** – Download a single video or audio file.
   - **Playlist to Text** – Download and process every item in a playlist.
   - **Local Files to Text** – Convert already downloaded media on your machine.
2. Select whether to download/convert **Video** or **Audio**.
3. Provide the URL or select the local files.
4. Press **Convert** to generate a `.txt` transcript for each file. When multiple transcripts are created, they can be merged automatically.
