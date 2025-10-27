"""
Main Client Application with GUI
Integrates all modules: video, audio, chat, file transfer, and screen sharing.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import socket
import threading
import pickle
import struct
import subprocess
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.protocol import *
from modules.text_chat import TextChat
from modules.file_transfer import FileTransfer
from modules.screen_sharing import ScreenSharing

class CommunicationClient:
    def __init__(self, root):
        self.root = root
        self.root.title("LAN Communication System")
        self.root.geometry("900x700")
        
        self.username = None
        self.server_ip = None
        self.tcp_socket = None
        self.running = False
        
        self.chat_module = None
        self.file_module = None
        self.screen_module = None
        
        self.video_process = None
        self.audio_capture_process = None
        self.audio_playback_process = None
        
        self.create_login_ui()
    
    def create_login_ui(self):
        """Create login screen."""
        login_frame = ttk.Frame(self.root, padding="20")
        login_frame.pack(expand=True)
        
        ttk.Label(login_frame, text="LAN Communication System", font=('Arial', 16, 'bold')).grid(row=0, column=0, columnspan=2, pady=20)
        
        ttk.Label(login_frame, text="Server IP:").grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.server_ip_entry = ttk.Entry(login_frame, width=30)
        self.server_ip_entry.insert(0, "127.0.0.1")
        self.server_ip_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(login_frame, text="Username:").grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.username_entry = ttk.Entry(login_frame, width=30)
        self.username_entry.grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Button(login_frame, text="Connect", command=self.connect_to_server).grid(row=3, column=0, columnspan=2, pady=20)
    
    def connect_to_server(self):
        """Connect to server and initialize all modules."""
        self.server_ip = self.server_ip_entry.get().strip()
        self.username = self.username_entry.get().strip()
        
        if not self.server_ip or not self.username:
            messagebox.showerror("Error", "Please enter both server IP and username")
            return
        
        try:
            # Connect TCP socket
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.connect((self.server_ip, TCP_PORT))
            
            # Register with server
            register_msg = {
                'type': MSG_REGISTER,
                'username': self.username
            }
            msg_data = pickle.dumps(register_msg)
            msg_length = struct.pack('!I', len(msg_data))
            self.tcp_socket.sendall(msg_length + msg_data)
            
            self.running = True
            
            # Initialize modules
            self.chat_module = TextChat(self.tcp_socket, self.username, self.on_chat_message)
            self.file_module = FileTransfer(self.tcp_socket, self.username, self.on_file_progress)
            self.screen_module = ScreenSharing(self.tcp_socket, self.username)
            
            # Start TCP receiver thread
            threading.Thread(target=self.receive_tcp, daemon=True).start()
            
            # Create main UI
            for widget in self.root.winfo_children():
                widget.destroy()
            self.create_main_ui()
            
            messagebox.showinfo("Success", f"Connected as {self.username}")
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect to server: {e}")
    
    def create_main_ui(self):
        """Create main application interface."""
        # Top frame for user info
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(top_frame, text=f"Connected as: {self.username}", font=('Arial', 10, 'bold')).pack(side='left')
        ttk.Label(top_frame, text=f"Server: {self.server_ip}", font=('Arial', 10)).pack(side='left', padx=20)
        
        # Notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Chat Tab
        chat_tab = ttk.Frame(notebook)
        notebook.add(chat_tab, text='Text Chat')
        self.create_chat_tab(chat_tab)
        
        # File Transfer Tab
        file_tab = ttk.Frame(notebook)
        notebook.add(file_tab, text='File Transfer')
        self.create_file_tab(file_tab)
        
        # Screen Sharing Tab
        screen_tab = ttk.Frame(notebook)
        notebook.add(screen_tab, text='Screen Sharing')
        self.create_screen_tab(screen_tab)
        
        # Video/Audio Tab
        media_tab = ttk.Frame(notebook)
        notebook.add(media_tab, text='Video/Audio')
        self.create_media_tab(media_tab)
        
        # Users Tab
        users_tab = ttk.Frame(notebook)
        notebook.add(users_tab, text='Users')
        self.create_users_tab(users_tab)
    
    def create_chat_tab(self, parent):
        """Create chat interface."""
        self.chat_display = scrolledtext.ScrolledText(parent, wrap=tk.WORD, height=20, state='disabled')
        self.chat_display.pack(expand=True, fill='both', padx=5, pady=5)
        
        input_frame = ttk.Frame(parent)
        input_frame.pack(fill='x', padx=5, pady=5)
        
        self.chat_entry = ttk.Entry(input_frame)
        self.chat_entry.pack(side='left', expand=True, fill='x', padx=(0, 5))
        self.chat_entry.bind('<Return>', lambda e: self.send_chat_message())
        
        ttk.Button(input_frame, text="Send", command=self.send_chat_message).pack(side='right')
    
    def create_file_tab(self, parent):
        """Create file transfer interface."""
        ttk.Label(parent, text="File Transfer", font=('Arial', 12, 'bold')).pack(pady=10)
        
        ttk.Button(parent, text="Select and Send File", command=self.send_file).pack(pady=10)
        
        ttk.Label(parent, text="Transfer Status:").pack(pady=5)
        self.file_status = scrolledtext.ScrolledText(parent, wrap=tk.WORD, height=15, state='disabled')
        self.file_status.pack(expand=True, fill='both', padx=5, pady=5)
    
    def create_screen_tab(self, parent):
        """Create screen sharing interface."""
        ttk.Label(parent, text="Screen Sharing Controls", font=('Arial', 12, 'bold')).pack(pady=10)
        
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text="Start Sharing", command=self.start_screen_share).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Stop Sharing", command=self.stop_screen_share).pack(side='left', padx=5)
        
        ttk.Label(parent, text="Status:").pack(pady=5)
        self.screen_status = tk.Label(parent, text="Not sharing", font=('Arial', 10))
        self.screen_status.pack()
        
        ttk.Label(parent, text="\nNote: Other users' shared screens will appear in separate windows.", wraplength=400).pack(pady=20)
    
    def create_media_tab(self, parent):
        """Create video/audio controls."""
        ttk.Label(parent, text="Video & Audio Controls", font=('Arial', 12, 'bold')).pack(pady=10)
        
        ttk.Label(parent, text="These controls launch separate processes for video and audio streaming.").pack(pady=10)
        
        # Video controls
        video_frame = ttk.LabelFrame(parent, text="Video Conferencing", padding="10")
        video_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Button(video_frame, text="Start Video Capture", command=self.start_video_capture).pack(pady=5)
        ttk.Button(video_frame, text="Start Video Display", command=self.start_video_display).pack(pady=5)
        
        # Audio controls
        audio_frame = ttk.LabelFrame(parent, text="Audio Conferencing", padding="10")
        audio_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Button(audio_frame, text="Start Audio Capture (Mic)", command=self.start_audio_capture).pack(pady=5)
        ttk.Button(audio_frame, text="Start Audio Playback (Speaker)", command=self.start_audio_playback).pack(pady=5)
        
        ttk.Label(parent, text="\nNote: Video display will open in a separate window showing all participants.", wraplength=400).pack(pady=20)
    
    def create_users_tab(self, parent):
        """Create users list."""
        ttk.Label(parent, text="Connected Users", font=('Arial', 12, 'bold')).pack(pady=10)
        
        self.users_listbox = tk.Listbox(parent, height=20)
        self.users_listbox.pack(expand=True, fill='both', padx=20, pady=10)
    
    def send_chat_message(self):
        """Send chat message."""
        message = self.chat_entry.get().strip()
        if message and self.chat_module:
            self.chat_module.send_message(message)
            self.chat_entry.delete(0, tk.END)
    
    def on_chat_message(self, message):
        """Callback for chat messages."""
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, message + '\n')
        self.chat_display.see(tk.END)
        self.chat_display.config(state='disabled')
    
    def send_file(self):
        """Select and send file."""
        filepath = filedialog.askopenfilename(title="Select file to send")
        if filepath and self.file_module:
            threading.Thread(target=self.file_module.send_file, args=(filepath,), daemon=True).start()
    
    def on_file_progress(self, status):
        """Callback for file transfer progress."""
        self.file_status.config(state='normal')
        self.file_status.insert(tk.END, status + '\n')
        self.file_status.see(tk.END)
        self.file_status.config(state='disabled')
    
    def start_screen_share(self):
        """Start screen sharing."""
        if self.screen_module:
            self.screen_module.start_sharing()
            self.screen_status.config(text="Sharing screen...")
    
    def stop_screen_share(self):
        """Stop screen sharing."""
        if self.screen_module:
            self.screen_module.stop_sharing()
            self.screen_status.config(text="Not sharing")
    
    def start_video_capture(self):
        """Start video capture process."""
        try:
            self.video_process = subprocess.Popen([
                'python3', 'modules/video_capture_encode.py',
                self.server_ip, self.username
            ], cwd='client')
            messagebox.showinfo("Video", "Video capture started")
        except Exception as e:
            messagebox.showerror("Error", f"Could not start video capture: {e}")
    
    def start_video_display(self):
        """Start video display process."""
        try:
            subprocess.Popen([
                'python3', 'modules/video_decode_render.py',
                self.server_ip, self.username
            ], cwd='client')
            messagebox.showinfo("Video", "Video display started in new window")
        except Exception as e:
            messagebox.showerror("Error", f"Could not start video display: {e}")
    
    def start_audio_capture(self):
        """Start audio capture process."""
        try:
            self.audio_capture_process = subprocess.Popen([
                'python3', 'modules/audio_capture_encode.py',
                self.server_ip, self.username
            ], cwd='client')
            messagebox.showinfo("Audio", "Audio capture started")
        except Exception as e:
            messagebox.showerror("Error", f"Could not start audio capture: {e}")
    
    def start_audio_playback(self):
        """Start audio playback process."""
        try:
            self.audio_playback_process = subprocess.Popen([
                'python3', 'modules/audio_decode_playback.py',
                self.server_ip, self.username
            ], cwd='client')
            messagebox.showinfo("Audio", "Audio playback started")
        except Exception as e:
            messagebox.showerror("Error", f"Could not start audio playback: {e}")
    
    def receive_tcp(self):
        """Receive TCP messages from server."""
        while self.running:
            try:
                length_data = self.recv_exact(4)
                if not length_data:
                    break
                
                msg_length = struct.unpack('!I', length_data)[0]
                msg_data = self.recv_exact(msg_length)
                if not msg_data:
                    break
                
                message = pickle.loads(msg_data)
                msg_type = message.get('type')
                
                if msg_type == MSG_CHAT:
                    self.chat_module.receive_message(message)
                    
                elif msg_type == MSG_FILE_META:
                    self.file_module.receive_file_meta(message)
                    
                elif msg_type == MSG_FILE_DATA:
                    self.file_module.receive_file_data(message)
                    
                elif msg_type == MSG_USER_LIST:
                    self.update_user_list(message.get('users', []))
                    
                elif msg_type == MSG_SCREEN_FRAME:
                    pass
                    
            except Exception as e:
                if self.running:
                    print(f"[ERROR] TCP receive: {e}")
                break
    
    def recv_exact(self, num_bytes):
        """Receive exact number of bytes."""
        data = b''
        while len(data) < num_bytes:
            chunk = self.tcp_socket.recv(num_bytes - len(data))
            if not chunk:
                return None
            data += chunk
        return data
    
    def update_user_list(self, users):
        """Update users list."""
        self.users_listbox.delete(0, tk.END)
        for user in users:
            self.users_listbox.insert(tk.END, user)
    
    def on_closing(self):
        """Handle window closing."""
        self.running = False
        if self.tcp_socket:
            self.tcp_socket.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CommunicationClient(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

