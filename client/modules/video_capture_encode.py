"""
Video Capture and Encode Node
Captures video from webcam, compresses it, and sends via UDP to server.
"""

import cv2
import socket
import pickle
import struct
import threading
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.protocol import *

class VideoCaptureNode:
    def __init__(self, server_ip, username):
        self.server_ip = server_ip
        self.username = username
        self.running = False
        self.capture = None
        self.socket = None
        
    def start(self):
        """Start video capture and transmission."""
        self.running = True
        self.capture = cv2.VideoCapture(0)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, VIDEO_WIDTH)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, VIDEO_HEIGHT)
        self.capture.set(cv2.CAP_PROP_FPS, VIDEO_FPS)
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        print(f"[VIDEO CAPTURE] Started for {self.username}")
        
        threading.Thread(target=self.capture_and_send, daemon=True).start()
    
    def capture_and_send(self):
        """Capture frames and send to server."""
        while self.running:
            try:
                ret, frame = self.capture.read()
                if not ret:
                    continue
                
                # Resize and encode frame
                frame = cv2.resize(frame, (VIDEO_WIDTH, VIDEO_HEIGHT))
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), VIDEO_QUALITY]
                _, encoded_frame = cv2.imencode('.jpg', frame, encode_param)
                
                # Create packet with username
                packet = {
                    'username': self.username,
                    'frame': encoded_frame.tobytes()
                }
                data = pickle.dumps(packet)
                
                # Split large packets if needed
                if len(data) < MAX_PACKET_SIZE:
                    self.socket.sendto(data, (self.server_ip, UDP_VIDEO_PORT))
                else:
                    print(f"[VIDEO CAPTURE] Packet too large: {len(data)} bytes")
                
            except Exception as e:
                print(f"[ERROR] Video capture: {e}")
    
    def stop(self):
        """Stop video capture."""
        self.running = False
        if self.capture:
            self.capture.release()
        if self.socket:
            self.socket.close()
        print("[VIDEO CAPTURE] Stopped")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python video_capture_encode.py <server_ip> <username>")
        sys.exit(1)
    
    node = VideoCaptureNode(sys.argv[1], sys.argv[2])
    node.start()
    
    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        node.stop()

