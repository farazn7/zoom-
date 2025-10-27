"""
Audio Decode and Playback Node
Receives mixed audio from server and plays through speakers.
"""

import pyaudio
import socket
import pickle
import threading
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.protocol import *

class AudioPlaybackNode:
    def __init__(self, server_ip, username):
        self.server_ip = server_ip
        self.username = username
        self.running = False
        self.audio = None
        self.stream = None
        self.socket = None
        
    def start(self):
        """Start receiving and playing audio."""
        self.running = True
        self.audio = pyaudio.PyAudio()
        
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=AUDIO_CHANNELS,
            rate=AUDIO_RATE,
            output=True,
            frames_per_buffer=AUDIO_CHUNK
        )
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', UDP_AUDIO_PORT + 1000))
        
        print(f"[AUDIO PLAYBACK] Started for {self.username} on port {UDP_AUDIO_PORT + 1000}")
        
        self.register_udp_port()
        
        threading.Thread(target=self.receive_and_play, daemon=True).start()
    
    def register_udp_port(self):
        """Register audio port with server via TCP."""
        try:
            tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_sock.connect((self.server_ip, TCP_PORT))
            
            message = {
                'type': MSG_UDP_REGISTER,
                'username': self.username,
                'video_port': None,
                'audio_port': UDP_AUDIO_PORT + 1000
            }
            
            msg_data = pickle.dumps(message)
            msg_length = struct.pack('!I', len(msg_data))
            tcp_sock.sendall(msg_length + msg_data)
            tcp_sock.close()
            
            print(f"[AUDIO PLAYBACK] Registered UDP port with server")
        except Exception as e:
            print(f"[ERROR] Audio port registration: {e}")
    
    def receive_and_play(self):
        """Receive audio packets and play them."""
        while self.running:
            try:
                data, _ = self.socket.recvfrom(MAX_PACKET_SIZE)
                packet = pickle.loads(data)
                
                username = packet.get('username')
                if username != self.username:
                    audio_data = packet.get('audio')
                    self.stream.write(audio_data)
                    
            except Exception as e:
                print(f"[ERROR] Audio playback: {e}")
    
    def stop(self):
        """Stop audio playback."""
        self.running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()
        if self.socket:
            self.socket.close()
        print("[AUDIO PLAYBACK] Stopped")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python audio_decode_playback.py <server_ip> <username>")
        sys.exit(1)
    
    node = AudioPlaybackNode(sys.argv[1], sys.argv[2])
    node.start()
    
    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        node.stop()

