"""
Main Server Application
Manages client connections, user registry, and acts as relay bridge for all communications.
Handles both TCP (chat, files, screen sharing) and UDP (video, audio) protocols.
"""

import socket
import threading
import pickle
import struct
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.protocol import *

class CommunicationServer:
    def __init__(self, host='0.0.0.0'):
        self.host = host
        self.clients = {}
        self.client_lock = threading.Lock()
        self.tcp_socket = None
        self.udp_video_socket = None
        self.udp_audio_socket = None
        self.running = False
        self.presenter = None
        
    def start(self):
        """Start all server sockets and listening threads."""
        self.running = True
        
        # TCP Socket for chat, file transfer, screen sharing
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind((self.host, TCP_PORT))
        self.tcp_socket.listen(5)
        print(f"[SERVER] TCP listening on {self.host}:{TCP_PORT}")
        
        # UDP Socket for video
        self.udp_video_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_video_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_video_socket.bind((self.host, UDP_VIDEO_PORT))
        print(f"[SERVER] UDP Video listening on {self.host}:{UDP_VIDEO_PORT}")
        
        # UDP Socket for audio
        self.udp_audio_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_audio_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_audio_socket.bind((self.host, UDP_AUDIO_PORT))
        print(f"[SERVER] UDP Audio listening on {self.host}:{UDP_AUDIO_PORT}")
        
        # Start listening threads
        threading.Thread(target=self.accept_tcp_connections, daemon=True).start()
        threading.Thread(target=self.handle_udp_video, daemon=True).start()
        threading.Thread(target=self.handle_udp_audio, daemon=True).start()
        
        print("[SERVER] Server is running. Press Ctrl+C to stop.")
        
        try:
            while self.running:
                threading.Event().wait(1)
        except KeyboardInterrupt:
            print("\n[SERVER] Shutting down...")
            self.stop()
    
    def accept_tcp_connections(self):
        """Accept incoming TCP client connections."""
        while self.running:
            try:
                client_socket, address = self.tcp_socket.accept()
                threading.Thread(target=self.handle_tcp_client, args=(client_socket, address), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"[ERROR] TCP accept: {e}")
    
    def handle_tcp_client(self, client_socket, address):
        """Handle TCP communication from a client."""
        username = None
        try:
            while self.running:
                # Receive message length (4 bytes)
                length_data = self.recv_exact(client_socket, 4)
                if not length_data:
                    break
                
                msg_length = struct.unpack('!I', length_data)[0]
                
                # Receive message data
                msg_data = self.recv_exact(client_socket, msg_length)
                if not msg_data:
                    break
                
                message = pickle.loads(msg_data)
                msg_type = message.get('type')
                
                if msg_type == MSG_REGISTER:
                    username = message.get('username')
                    with self.client_lock:
                        self.clients[username] = {
                            'tcp_socket': client_socket,
                            'address': address,
                            'video_port': None,
                            'audio_port': None
                        }
                    print(f"[SERVER] User registered: {username} from {address}")
                    self.broadcast_user_list()
                    
                elif msg_type == MSG_UDP_REGISTER:
                    video_port = message.get('video_port')
                    audio_port = message.get('audio_port')
                    reg_username = message.get('username')
                    with self.client_lock:
                        if reg_username in self.clients:
                            if video_port is not None:
                                self.clients[reg_username]['video_port'] = video_port
                            if audio_port is not None:
                                self.clients[reg_username]['audio_port'] = audio_port
                    print(f"[SERVER] UDP registered for {reg_username}: video={video_port}, audio={audio_port}")
                    
                elif msg_type == MSG_CHAT:
                    self.broadcast_tcp(message, exclude=username)
                    print(f"[CHAT] {message.get('username')}: {message.get('message')}")
                    
                elif msg_type == MSG_FILE_META:
                    self.broadcast_tcp(message, exclude=username)
                    print(f"[FILE] {username} sharing: {message.get('filename')}")
                    
                elif msg_type == MSG_FILE_REQUEST:
                    self.broadcast_tcp(message)
                    
                elif msg_type == MSG_FILE_DATA:
                    self.broadcast_tcp(message, exclude=username)
                    
                elif msg_type == MSG_SCREEN_START:
                    self.presenter = username
                    self.broadcast_tcp(message, exclude=username)
                    print(f"[SCREEN] {username} started screen sharing")
                    
                elif msg_type == MSG_SCREEN_STOP:
                    self.presenter = None
                    self.broadcast_tcp(message, exclude=username)
                    print(f"[SCREEN] {username} stopped screen sharing")
                    
                elif msg_type == MSG_SCREEN_FRAME:
                    self.broadcast_tcp(message, exclude=username)
                    
        except Exception as e:
            print(f"[ERROR] TCP client {username}: {e}")
        finally:
            if username:
                with self.client_lock:
                    if username in self.clients:
                        del self.clients[username]
                print(f"[SERVER] User disconnected: {username}")
                self.broadcast_user_list()
            client_socket.close()
    
    def handle_udp_video(self):
        """Handle incoming UDP video packets and broadcast to all clients."""
        while self.running:
            try:
                data, address = self.udp_video_socket.recvfrom(MAX_PACKET_SIZE)
                
                # Broadcast to all clients with registered video ports
                with self.client_lock:
                    for username, client_info in self.clients.items():
                        try:
                            video_port = client_info.get('video_port')
                            if video_port:
                                client_address = client_info['address']
                                self.udp_video_socket.sendto(data, (client_address[0], video_port))
                        except Exception as e:
                            print(f"[ERROR] UDP video send to {username}: {e}")
            except Exception as e:
                if self.running:
                    print(f"[ERROR] UDP video: {e}")
    
    def handle_udp_audio(self):
        """Handle incoming UDP audio packets, mix, and broadcast to all clients."""
        audio_buffer = {}
        
        while self.running:
            try:
                data, address = self.udp_audio_socket.recvfrom(MAX_PACKET_SIZE)
                
                # Simple broadcast (mixing would require numpy audio processing)
                with self.client_lock:
                    for username, client_info in self.clients.items():
                        try:
                            audio_port = client_info.get('audio_port')
                            if audio_port:
                                client_address = client_info['address']
                                self.udp_audio_socket.sendto(data, (client_address[0], audio_port))
                        except Exception as e:
                            print(f"[ERROR] UDP audio send to {username}: {e}")
            except Exception as e:
                if self.running:
                    print(f"[ERROR] UDP audio: {e}")
    
    def broadcast_tcp(self, message, exclude=None):
        """Broadcast TCP message to all clients except excluded username."""
        msg_data = pickle.dumps(message)
        msg_length = struct.pack('!I', len(msg_data))
        
        with self.client_lock:
            for username, client_info in self.clients.items():
                if username != exclude:
                    try:
                        client_info['tcp_socket'].sendall(msg_length + msg_data)
                    except Exception as e:
                        print(f"[ERROR] Broadcast to {username}: {e}")
    
    def broadcast_user_list(self):
        """Broadcast current user list to all connected clients."""
        with self.client_lock:
            user_list = list(self.clients.keys())
        
        message = {
            'type': MSG_USER_LIST,
            'users': user_list
        }
        self.broadcast_tcp(message)
    
    def recv_exact(self, sock, num_bytes):
        """Receive exact number of bytes from socket."""
        data = b''
        while len(data) < num_bytes:
            chunk = sock.recv(num_bytes - len(data))
            if not chunk:
                return None
            data += chunk
        return data
    
    def stop(self):
        """Stop the server and close all sockets."""
        self.running = False
        
        if self.tcp_socket:
            self.tcp_socket.close()
        if self.udp_video_socket:
            self.udp_video_socket.close()
        if self.udp_audio_socket:
            self.udp_audio_socket.close()
        
        print("[SERVER] Server stopped.")

if __name__ == "__main__":
    server = CommunicationServer()
    server.start()

