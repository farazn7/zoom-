"""
Video Decode and Render Node
Receives compressed video from server, decodes, and displays multiple streams.
"""

import cv2
import socket
import pickle
import numpy as np
import threading
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.protocol import *

class VideoRenderNode:
    def __init__(self, server_ip, username):
        self.server_ip = server_ip
        self.username = username
        self.running = False
        self.socket = None
        self.video_streams = {}
        self.stream_lock = threading.Lock()
        
    def start(self):
        """Start receiving and rendering video."""
        self.running = True
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', UDP_VIDEO_PORT + 1000))
        
        print(f"[VIDEO RENDER] Started for {self.username} on port {UDP_VIDEO_PORT + 1000}")
        
        self.register_udp_port()
        
        threading.Thread(target=self.receive_video, daemon=True).start()
        threading.Thread(target=self.display_video, daemon=True).start()
    
    def register_udp_port(self):
        """Register video port with server via TCP."""
        try:
            tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_sock.connect((self.server_ip, TCP_PORT))
            
            message = {
                'type': MSG_UDP_REGISTER,
                'username': self.username,
                'video_port': UDP_VIDEO_PORT + 1000,
                'audio_port': None
            }
            
            msg_data = pickle.dumps(message)
            msg_length = struct.pack('!I', len(msg_data))
            tcp_sock.sendall(msg_length + msg_data)
            tcp_sock.close()
            
            print(f"[VIDEO RENDER] Registered UDP port with server")
        except Exception as e:
            print(f"[ERROR] Video port registration: {e}")
    
    def receive_video(self):
        """Receive video packets from server."""
        while self.running:
            try:
                data, _ = self.socket.recvfrom(MAX_PACKET_SIZE)
                packet = pickle.loads(data)
                
                username = packet.get('username')
                if username != self.username:
                    frame_data = packet.get('frame')
                    
                    # Decode frame
                    nparr = np.frombuffer(frame_data, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    with self.stream_lock:
                        self.video_streams[username] = frame
                        
            except Exception as e:
                print(f"[ERROR] Video receive: {e}")
    
    def display_video(self):
        """Display all video streams in a grid layout."""
        while self.running:
            try:
                with self.stream_lock:
                    streams = list(self.video_streams.items())
                
                if not streams:
                    cv2.waitKey(1)
                    continue
                
                # Create grid layout
                num_streams = len(streams)
                cols = int(np.ceil(np.sqrt(num_streams)))
                rows = int(np.ceil(num_streams / cols))
                
                grid_frames = []
                for i in range(rows):
                    row_frames = []
                    for j in range(cols):
                        idx = i * cols + j
                        if idx < num_streams:
                            username, frame = streams[idx]
                            frame = cv2.resize(frame, (320, 240))
                            cv2.putText(frame, username, (10, 30), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                            row_frames.append(frame)
                        else:
                            row_frames.append(np.zeros((240, 320, 3), dtype=np.uint8))
                    
                    if row_frames:
                        grid_frames.append(np.hstack(row_frames))
                
                if grid_frames:
                    grid = np.vstack(grid_frames)
                    cv2.imshow('Video Conference', grid)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.stop()
                    
            except Exception as e:
                print(f"[ERROR] Video display: {e}")
    
    def stop(self):
        """Stop video rendering."""
        self.running = False
        if self.socket:
            self.socket.close()
        cv2.destroyAllWindows()
        print("[VIDEO RENDER] Stopped")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python video_decode_render.py <server_ip> <username>")
        sys.exit(1)
    
    node = VideoRenderNode(sys.argv[1], sys.argv[2])
    node.start()
    
    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        node.stop()

