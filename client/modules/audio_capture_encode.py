"""
Audio Capture and Encode Node
Captures audio from microphone, encodes it, and sends via UDP to server.
"""

import pyaudio
import socket
import pickle
import threading
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.protocol import *

class AudioCaptureNode:
    def __init__(self, server_ip, username):
        self.server_ip = server_ip
        self.username = username
        self.running = False
        self.audio = None
        self.stream = None
        self.socket = None
        
    def start(self):
        """Start audio capture and transmission."""
        self.running = True
        self.audio = pyaudio.PyAudio()
        
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=AUDIO_CHANNELS,
            rate=AUDIO_RATE,
            input=True,
            frames_per_buffer=AUDIO_CHUNK
        )
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        print(f"[AUDIO CAPTURE] Started for {self.username}")
        
        threading.Thread(target=self.capture_and_send, daemon=True).start()
    
    def capture_and_send(self):
        """Capture audio and send to server."""
        while self.running:
            try:
                audio_data = self.stream.read(AUDIO_CHUNK, exception_on_overflow=False)
                
                packet = {
                    'username': self.username,
                    'audio': audio_data
                }
                data = pickle.dumps(packet)
                
                if len(data) < MAX_PACKET_SIZE:
                    self.socket.sendto(data, (self.server_ip, UDP_AUDIO_PORT))
                    
            except Exception as e:
                print(f"[ERROR] Audio capture: {e}")
    
    def stop(self):
        """Stop audio capture."""
        self.running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()
        if self.socket:
            self.socket.close()
        print("[AUDIO CAPTURE] Stopped")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python audio_capture_encode.py <server_ip> <username>")
        sys.exit(1)
    
    node = AudioCaptureNode(sys.argv[1], sys.argv[2])
    node.start()
    
    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        node.stop()

