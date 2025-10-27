"""
File Transfer Module
Handles file uploads and downloads with progress tracking.
"""

import os
import pickle
import struct
import threading
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.protocol import *

class FileTransfer:
    def __init__(self, tcp_socket, username, progress_callback=None):
        self.tcp_socket = tcp_socket
        self.username = username
        self.progress_callback = progress_callback
        self.available_files = {}
        
    def send_file(self, filepath):
        """Send file to server for distribution."""
        try:
            if not os.path.exists(filepath):
                print(f"[ERROR] File not found: {filepath}")
                return
            
            filename = os.path.basename(filepath)
            filesize = os.path.getsize(filepath)
            
            # Send file metadata
            meta_message = {
                'type': MSG_FILE_META,
                'username': self.username,
                'filename': filename,
                'filesize': filesize
            }
            self.send_tcp(meta_message)
            
            # Send file data in chunks
            with open(filepath, 'rb') as f:
                sent = 0
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    
                    data_message = {
                        'type': MSG_FILE_DATA,
                        'username': self.username,
                        'filename': filename,
                        'data': chunk,
                        'offset': sent
                    }
                    self.send_tcp(data_message)
                    
                    sent += len(chunk)
                    if self.progress_callback:
                        progress = int((sent / filesize) * 100)
                        self.progress_callback(f"Sending: {progress}%")
            
            print(f"[FILE] Sent: {filename} ({filesize} bytes)")
            if self.progress_callback:
                self.progress_callback(f"Sent: {filename}")
                
        except Exception as e:
            print(f"[ERROR] File send: {e}")
    
    def receive_file_meta(self, message):
        """Handle file metadata from server."""
        filename = message.get('filename')
        filesize = message.get('filesize')
        sender = message.get('username')
        
        self.available_files[filename] = {
            'sender': sender,
            'size': filesize,
            'received_data': {}
        }
        
        if self.progress_callback:
            self.progress_callback(f"Available: {filename} from {sender} ({filesize} bytes)")
    
    def receive_file_data(self, message):
        """Handle file data chunks from server."""
        filename = message.get('filename')
        data = message.get('data')
        offset = message.get('offset')
        
        if filename in self.available_files:
            self.available_files[filename]['received_data'][offset] = data
            
            # Check if file is complete
            total_received = sum(len(d) for d in self.available_files[filename]['received_data'].values())
            total_size = self.available_files[filename]['size']
            
            if total_received >= total_size:
                self.save_file(filename)
    
    def save_file(self, filename):
        """Save received file to downloads folder."""
        try:
            downloads_dir = 'downloads'
            os.makedirs(downloads_dir, exist_ok=True)
            
            filepath = os.path.join(downloads_dir, filename)
            file_info = self.available_files[filename]
            
            with open(filepath, 'wb') as f:
                sorted_offsets = sorted(file_info['received_data'].keys())
                for offset in sorted_offsets:
                    f.write(file_info['received_data'][offset])
            
            print(f"[FILE] Received: {filename}")
            if self.progress_callback:
                self.progress_callback(f"Downloaded: {filename}")
            
        except Exception as e:
            print(f"[ERROR] File save: {e}")
    
    def send_tcp(self, message):
        """Send TCP message."""
        try:
            msg_data = pickle.dumps(message)
            msg_length = struct.pack('!I', len(msg_data))
            self.tcp_socket.sendall(msg_length + msg_data)
        except Exception as e:
            print(f"[ERROR] TCP send: {e}")

