"""
Screen Sharing Module
Allows presenter to capture and share screen using TCP for reliability.
"""

import mss
import numpy as np
import cv2
import pickle
import struct
import threading
import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.protocol import *

class ScreenSharing:
    def __init__(self, tcp_socket, username):
        self.tcp_socket = tcp_socket
        self.username = username
        self.sharing = False
        self.share_thread = None
        
    def start_sharing(self):
        """Start screen sharing."""
        if self.sharing:
            return
        
        self.sharing = True
        
        # Send start message
        message = {
            'type': MSG_SCREEN_START,
            'username': self.username
        }
        self.send_tcp(message)
        
        self.share_thread = threading.Thread(target=self.capture_and_send, daemon=True)
        self.share_thread.start()
        
        print(f"[SCREEN SHARE] Started sharing")
    
    def stop_sharing(self):
        """Stop screen sharing."""
        if not self.sharing:
            return
        
        self.sharing = False
        
        # Send stop message
        message = {
            'type': MSG_SCREEN_STOP,
            'username': self.username
        }
        self.send_tcp(message)
        
        print(f"[SCREEN SHARE] Stopped sharing")
    
    def capture_and_send(self):
        """Capture screen and send frames to server."""
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            
            while self.sharing:
                try:
                    # Capture screen
                    screenshot = sct.grab(monitor)
                    frame = np.array(screenshot)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    
                    # Resize for bandwidth
                    frame = cv2.resize(frame, (1024, 768))
                    
                    # Encode
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
                    _, encoded = cv2.imencode('.jpg', frame, encode_param)
                    
                    # Send frame
                    message = {
                        'type': MSG_SCREEN_FRAME,
                        'username': self.username,
                        'frame': encoded.tobytes()
                    }
                    self.send_tcp(message)
                    
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"[ERROR] Screen capture: {e}")
    
    def send_tcp(self, message):
        """Send TCP message."""
        try:
            msg_data = pickle.dumps(message)
            msg_length = struct.pack('!I', len(msg_data))
            self.tcp_socket.sendall(msg_length + msg_data)
        except Exception as e:
            print(f"[ERROR] TCP send: {e}")

