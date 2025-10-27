# LAN Communication System

A comprehensive multi-user communication application for Local Area Network (LAN) environments, built with Python socket programming.

## Features

- **Multi-User Video Conferencing**: Real-time video streaming using UDP
- **Multi-User Audio Conferencing**: Real-time audio streaming using UDP with mixing
- **Group Text Chat**: Reliable text messaging using TCP
- **File Transfer**: Send and receive files with progress tracking (TCP)
- **Screen Sharing**: Share your screen with all participants (TCP)

## Architecture

The application uses a modular architecture with separate nodes for different functionalities:

### Server (`server/`)
- `server_main.py`: Central relay managing connections and broadcasting data

### Client (`client/`)
- `client_main.py`: Main GUI application integrating all modules
- `modules/`:
  - `video_capture_encode.py`: Captures and encodes video
  - `video_decode_render.py`: Decodes and displays video streams
  - `audio_capture_encode.py`: Captures and encodes audio
  - `audio_decode_playback.py`: Decodes and plays audio
  - `screen_sharing.py`: Screen capture and sharing
  - `file_transfer.py`: File upload/download
  - `text_chat.py`: Text messaging

### Shared (`shared/`)
- `protocol.py`: Shared protocol definitions and constants

## Requirements

- Python 3.11+
- opencv-python (cv2)
- pyaudio
- Pillow (PIL)
- numpy
- mss

## Installation

```bash
# Install dependencies
pip install opencv-python pyaudio pillow numpy mss
```

## Usage

### Starting the Server

```bash
python server/server_main.py
```

The server will listen on:
- TCP Port 5555 (chat, files, screen sharing)
- UDP Port 5556 (video)
- UDP Port 5557 (audio)

### Starting the Client

```bash
python client/client_main.py
```

1. Enter the server IP address (use `127.0.0.1` for local testing)
2. Enter your username
3. Click "Connect"

### Using the Application

**Text Chat:**
- Navigate to "Text Chat" tab
- Type messages and press Enter or click Send

**File Transfer:**
- Navigate to "File Transfer" tab
- Click "Select and Send File"
- Received files are saved in `downloads/` folder

**Screen Sharing:**
- Navigate to "Screen Sharing" tab
- Click "Start Sharing" to share your screen
- Click "Stop Sharing" to stop

**Video/Audio:**
- Navigate to "Video/Audio" tab
- Click "Start Video Capture" to send your video
- Click "Start Video Display" to see others (opens new window)
- Click "Start Audio Capture (Mic)" to send audio
- Click "Start Audio Playback (Speaker)" to hear others

## Network Protocol

### TCP (Reliable):
- User registration
- Text chat messages
- File transfers with metadata
- Screen sharing frames

### UDP (Low Latency):
- Video frames (compressed JPEG)
- Audio packets (raw audio data)

## File Structure

```
.
├── server/
│   └── server_main.py
├── client/
│   ├── client_main.py
│   └── modules/
│       ├── video_capture_encode.py
│       ├── video_decode_render.py
│       ├── audio_capture_encode.py
│       ├── audio_decode_playback.py
│       ├── screen_sharing.py
│       ├── file_transfer.py
│       └── text_chat.py
├── shared/
│   └── protocol.py
└── README.md
```

## Notes

- All communication happens over LAN - no internet required
- UTF-8 encoding used for text data
- Video quality and resolution can be adjusted in `shared/protocol.py`
- Audio is mixed on the server side before broadcasting
- File transfers show progress in the UI

