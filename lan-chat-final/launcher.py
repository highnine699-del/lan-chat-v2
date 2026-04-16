import tkinter as tk
from tkinter import messagebox
import subprocess
import threading
import webbrowser
import socket
import time
import os
import sys
import shutil

class LanChatLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("LAN Chat Server")
        self.root.geometry("500x350")
        self.root.resizable(False, False)
        self.server_process = None
        self.ngrok_process = None
        self.is_running = False
        self.public_url = None
        self.local_ip = None
        
        # Title
        title = tk.Label(root, text="LAN Chat Server", font=("Arial", 18, "bold"))
        title.pack(pady=15)
        
        # Local IP Display
        self.ip_label = tk.Label(root, text="Local IP: Detecting...", font=("Arial", 10), fg="blue")
        self.ip_label.pack(pady=5)
        
        # Public URL Display
        self.url_label = tk.Label(root, text="Public URL: Not connected", font=("Arial", 10), fg="orange")
        self.url_label.pack(pady=5)
        
        # Status label
        self.status_label = tk.Label(root, text="Status: Stopped", font=("Arial", 10), fg="red")
        self.status_label.pack(pady=10)
        
        # Start button
        self.start_btn = tk.Button(root, text="START SERVER", command=self._start_server, 
                                   bg="#25D366", fg="white", font=("Arial", 12, "bold"), 
                                   padx=20, pady=10, cursor="hand2")
        self.start_btn.pack(pady=10)
        
        # Stop button
        self.stop_btn = tk.Button(root, text="STOP SERVER", command=self._stop_server, 
                                  bg="#ff4444", fg="white", font=("Arial", 12, "bold"), 
                                  padx=20, pady=10, cursor="hand2", state=tk.DISABLED)
        self.stop_btn.pack(pady=5)
        
        # Open browser button
        self.browser_btn = tk.Button(root, text="OPEN IN BROWSER", command=self._open_browser, 
                                     font=("Arial", 10), padx=15, pady=8, state=tk.DISABLED)
        self.browser_btn.pack(pady=5)
        
        # Copy URL button
        self.copy_btn = tk.Button(root, text="COPY PUBLIC URL", command=self._copy_url, 
                                  font=("Arial", 10), padx=15, pady=8, state=tk.DISABLED)
        self.copy_btn.pack(pady=5)
        
        # Get IP in background
        threading.Thread(target=self._get_local_ip, daemon=True).start()
        
    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            self.local_ip = s.getsockname()[0]
            s.close()
            self.ip_label.config(text=f"Local IP: http://{self.local_ip}:5000", fg="green")
        except:
            self.ip_label.config(text="Local IP: http://localhost:5000", fg="orange")
            self.local_ip = "localhost"
    
    def _find_ngrok(self):
        """Find ngrok executable"""
        # Check PATH
        ngrok_path = shutil.which("ngrok")
        if ngrok_path:
            return ngrok_path
        
        # Check common locations
        common_paths = [
            "C:\\Program Files\\WindowsApps\\ngrok.ngrok_3.36.1.0_x64__1g87z0zv29zzc\\ngrok.exe",
            "C:\\Program Files\\ngrok\\ngrok.exe",
            "C:\\Program Files (x86)\\ngrok\\ngrok.exe",
            os.path.expanduser("~\\Downloads\\ngrok.exe"),
            os.path.expanduser("~\\ngrok.exe"),
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def _start_server(self):
        if self.is_running:
            messagebox.showwarning("Info", "Server is already running!")
            return
        
        # Find ngrok
        ngrok_path = self._find_ngrok()
        if not ngrok_path:
            messagebox.showerror("Error", "ngrok not found!\n\nPlease:\n1. Download ngrok from ngrok.com\n2. Add it to PATH or put it in your Downloads folder")
            return
        
        try:
            # Start server in background
            self.server_process = subprocess.Popen(
                [sys.executable, "server.py"],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
            )
            
            self.is_running = True
            self.status_label.config(text="Status: Starting ngrok...", fg="orange")
            self.root.update()
            
            # Start ngrok in background
            self.ngrok_path = ngrok_path
            threading.Thread(target=self._start_ngrok, daemon=True).start()
            
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.browser_btn.config(state=tk.NORMAL)
            
            # Auto-open browser after a short delay
            threading.Thread(target=self._auto_open_browser, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server: {e}")
            self.status_label.config(text="Status: Stopped", fg="red")
    
    def _start_ngrok(self):
        """Start ngrok tunnel using local executable"""
        try:
            # Start ngrok process
            self.ngrok_process = subprocess.Popen(
                [self.ngrok_path, "http", "5000"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Poll the ngrok API until it responds or we time out (10 s).
            # A fixed sleep(2) is unreliable on slow machines.
            import urllib.request as _urllib
            import json as _json
            tunnels = []
            deadline = time.time() + 10
            while time.time() < deadline:
                try:
                    with _urllib.urlopen(
                        "http://localhost:4040/api/tunnels", timeout=1
                    ) as resp:
                        tunnels = _json.loads(resp.read()).get("tunnels", [])
                    if tunnels:
                        break
                except Exception:
                    pass
                time.sleep(0.5)

            if tunnels:
                self.public_url = tunnels[0].get("public_url")
                self.url_label.config(text=f"Public URL: {self.public_url}", fg="green")
                self.status_label.config(text="Status: Running ✓", fg="green")
                self.copy_btn.config(state=tk.NORMAL)
                return

            self.url_label.config(text="Public URL: ngrok started (check terminal for URL)", fg="orange")
            self.status_label.config(text="Status: Running ✓", fg="green")
            
        except Exception as e:
            self.url_label.config(text=f"Error: {str(e)[:40]}", fg="red")
            self.status_label.config(text="Status: Server running (ngrok failed)", fg="orange")
    
    def _auto_open_browser(self):
        time.sleep(2)  # Wait for server to start
        self._open_browser()
    
    def _open_browser(self):
        if self.public_url:
            webbrowser.open(self.public_url)
        else:
            url = f"http://{self.local_ip}:5000" if self.local_ip else "http://localhost:5000"
            webbrowser.open(url)
    
    def _copy_url(self):
        if self.public_url:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.public_url)
            messagebox.showinfo("Copied!", f"Public URL copied to clipboard:\n{self.public_url}")
        else:
            messagebox.showwarning("Error", "Public URL not available yet!")
    
    def _stop_server(self):
        if not self.is_running:
            return
        
        try:
            # Stop ngrok
            if self.ngrok_process:
                self.ngrok_process.terminate()
                self.ngrok_process.wait(timeout=5)
            
            # Stop server
            if self.server_process:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            
            self.is_running = False
            self.public_url = None
            self.status_label.config(text="Status: Stopped", fg="red")
            self.url_label.config(text="Public URL: Not connected", fg="orange")
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.browser_btn.config(state=tk.DISABLED)
            self.copy_btn.config(state=tk.DISABLED)
            messagebox.showinfo("Info", "Server stopped!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop server: {e}")
    
    def on_closing(self):
        if self.is_running:
            if messagebox.askokcancel("Quit", "Server is running. Stop it and quit?"):
                self._stop_server()
                self.root.destroy()
        else:
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = LanChatLauncher(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
