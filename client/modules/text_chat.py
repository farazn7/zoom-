"""
Text Chat Module
Handles group text messaging with chronological display.
"""

import pickle
import struct
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.protocol import *

class TextChat:
    def __init__(self, tcp_socket, username, message_callback=None):
        self.tcp_socket = tcp_socket
        self.username = username
        self.message_callback = message_callback
        self.chat_history = []
        
    def send_message(self, message_text):
        """Send chat message to server."""
        try:
            message = {
                'type': MSG_CHAT,
                'username': self.username,
                'message': message_text
            }
            
            msg_data = pickle.dumps(message)
            msg_length = struct.pack('!I', len(msg_data))
            self.tcp_socket.sendall(msg_length + msg_data)
            
            # Add to local history
            self.chat_history.append(f"{self.username}: {message_text}")
            if self.message_callback:
                self.message_callback(f"{self.username}: {message_text}")
                
        except Exception as e:
            print(f"[ERROR] Chat send: {e}")
    
    def receive_message(self, message):
        """Handle received chat message."""
        username = message.get('username')
        text = message.get('message')
        
        chat_line = f"{username}: {text}"
        self.chat_history.append(chat_line)
        
        if self.message_callback:
            self.message_callback(chat_line)
    
    def get_history(self):
        """Get chat history."""
        return self.chat_history

