#!/usr/bin/env python3
"""
Interactive TUI HTTP Upload/Download Server

Usage:
    python upload-server.py <port> [path] [--ip <ip>]
    
Examples:
    python upload-server.py 8000
    python upload-server.py 8000 /tmp/shared --ip 10.10.14.5

Requirements:
    pip install textual
"""

import os
import sys
import subprocess
import argparse
import threading
import re
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
from typing import List, Dict, Optional

from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Header, Footer, Static, DataTable, Input, Label
from textual.binding import Binding
from textual.screen import ModalScreen

BASE_DIR = "."  # default to current dir


# ============================================================================
# HTTP Server Components
# ============================================================================

def get_tun0_ip():
    """Get the IP address of tun0 interface"""
    try:
        ip = subprocess.check_output("ip addr show tun0", shell=True).decode()
        match = re.search(r"inet\s(\d+\.\d+\.\d+\.\d+)", ip)
        if match:
            return match.group(1)
        else:
            return None
    except Exception:
        return None


class Handler(BaseHTTPRequestHandler):
    """Custom HTTP request handler for upload/download operations"""
    
    def log_message(self, format, *args):
        """Suppress default logging to avoid interfering with TUI"""
        pass
    
    def do_PUT(self):
        length = int(self.headers['Content-Length'])
        filename = self.path.lstrip("/")
        
        # Save uploads to uploads/ subdirectory
        uploads_dir = os.path.join(BASE_DIR, "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        
        path = os.path.join(uploads_dir, filename)
        with open(path, "wb") as f:
            f.write(self.rfile.read(length))
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        self.do_PUT()  # Same handler for simplicity

    def do_GET(self):
        filename = self.path.lstrip("/")
        
        # Try uploads/ directory first, then base directory
        uploads_path = os.path.join(BASE_DIR, "uploads", filename)
        base_path = os.path.join(BASE_DIR, filename)
        
        path = uploads_path if os.path.isfile(uploads_path) else base_path
        
        if os.path.isfile(path):
            self.send_response(200)
            self.send_header('Content-type', 'application/octet-stream')
            self.end_headers()
            with open(path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"File not found.\n")


def run_server(port: int, base_dir: str):
    """Run the HTTP server in a separate thread"""
    global BASE_DIR
    BASE_DIR = base_dir
    
    # Create uploads directory if it doesn't exist
    uploads_dir = os.path.join(base_dir, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    
    server_address = ('', port)
    httpd = HTTPServer(server_address, Handler)
    httpd.serve_forever()


# ============================================================================
# File List Model
# ============================================================================

class FileListModel:
    """Model for discovering and tracking files in the served directory"""
    
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.files: List[Dict] = []
    
    def refresh(self) -> List[Dict]:
        """Scan directory and return list of files with metadata"""
        files = []
        try:
            if not os.path.exists(self.base_dir):
                return files
            
            # Scan base directory for files
            for filename in os.listdir(self.base_dir):
                filepath = os.path.join(self.base_dir, filename)
                if os.path.isfile(filepath):
                    stat = os.stat(filepath)
                    files.append({
                        'name': filename,
                        'size': stat.st_size,
                        'mtime': stat.st_mtime,
                        'md5': self.calculate_md5(filepath)
                    })
            
            # Scan uploads/ subdirectory if it exists
            uploads_dir = os.path.join(self.base_dir, "uploads")
            if os.path.exists(uploads_dir) and os.path.isdir(uploads_dir):
                for filename in os.listdir(uploads_dir):
                    filepath = os.path.join(uploads_dir, filename)
                    if os.path.isfile(filepath):
                        stat = os.stat(filepath)
                        files.append({
                            'name': f"uploads/{filename}",
                            'size': stat.st_size,
                            'mtime': stat.st_mtime,
                            'md5': self.calculate_md5(filepath)
                        })
            
            # Sort by modification time (newest first)
            files.sort(key=lambda x: x['mtime'], reverse=True)
            self.files = files
        except Exception as e:
            # Silently handle errors
            pass
        
        return self.files
    
    @staticmethod
    def calculate_md5(filepath: str) -> str:
        """Calculate MD5 hash of a file"""
        try:
            hash_md5 = hashlib.md5()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return "error"
    
    @staticmethod
    def format_size(size: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}PB"
    
    @staticmethod
    def format_time(timestamp: float) -> str:
        """Format timestamp in readable format"""
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime('%Y-%m-%d %H:%M')


# ============================================================================
# Command Generator
# ============================================================================

class CommandGenerator:
    """Generate download commands for files"""
    
    @staticmethod
    def generate_commands(ip: str, port: int, filename: str) -> Dict[str, str]:
        """Generate various download command formats"""
        url = f"http://{ip}:{port}/{filename}"
        # Use just the basename for output filename
        outfile = os.path.basename(filename)
        
        return {
            'url': url,
            'wget': f'wget {url} -O {outfile}',
            'iwr_short': f'iwr -uri {url} -Outfile {outfile}',
            'iwr_full': f'Invoke-WebRequest -Uri {url} -Outfile {outfile}',
            'certutil': f'certutil.exe -urlcache -split -f {url} {outfile}'
        }
    
    @staticmethod
    def generate_upload_commands(ip: str, port: int, filename: str) -> Dict[str, str]:
        """Generate upload command formats for PUT and POST"""
        url = f"http://{ip}:{port}/{filename}"
        
        return {
            'url': url,
            'curl_put': f'curl.exe -X PUT --upload-file {filename} {url}',
            'curl_post': f'curl.exe -X POST --data-binary @{filename} {url}',
            'wget_put': f'wget --method=PUT --body-file={filename} {url}',
            'wget_post': f'wget --method=POST --body-file={filename} {url}',
            'ps_put': f'Invoke-WebRequest -Uri {url} -Method PUT -InFile {filename}',
            'ps_post': f'Invoke-WebRequest -Uri {url} -Method POST -InFile {filename}'
        }


# ============================================================================
# TUI Widgets
# ============================================================================

class FileBrowser(Static):
    """File browser widget showing available files"""
    
    def __init__(self, file_model: FileListModel, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_model = file_model
        self.table = None
    
    def compose(self) -> ComposeResult:
        self.table = DataTable()
        self.table.add_column("Filename", width=30)
        self.table.add_column("Size", width=10)
        self.table.add_column("Modified", width=16)
        self.table.add_column("MD5", width=32)
        self.table.cursor_type = "row"
        yield self.table
    
    def on_mount(self) -> None:
        """Initialize table when widget is mounted"""
        self.refresh_files()
    
    def refresh_files(self) -> None:
        """Refresh the file list display"""
        # Remember the currently selected file
        selected_filename = self.get_selected_file()
        
        files = self.file_model.refresh()
        self.table.clear()
        
        if not files:
            self.table.add_row("(No files found)", "-", "-", "-")
        else:
            for file_info in files:
                self.table.add_row(
                    file_info['name'],
                    self.file_model.format_size(file_info['size']),
                    self.file_model.format_time(file_info['mtime']),
                    file_info['md5']
                )
            
            # Try to restore selection to the same file
            if files and self.table.row_count > 0:
                target_row = 0  # Default to first file
                
                if selected_filename:
                    # Find the previously selected file in the new list
                    for idx, file_info in enumerate(files):
                        if file_info['name'] == selected_filename:
                            target_row = idx
                            break
                
                self.table.move_cursor(row=target_row)
    
    def get_selected_file(self) -> Optional[str]:
        """Get the currently selected filename"""
        files = self.file_model.files
        if not files:
            return None
        
        cursor_row = self.table.cursor_row
        if 0 <= cursor_row < len(files):
            return files[cursor_row]['name']
        return None


class CommandsPanel(Static):
    """Commands panel showing download or upload commands"""
    
    def __init__(self, ip: str, port: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ip = ip
        self.port = port
        self.current_filename = None
        self.mode = "download"
        self.upload_filename = None
    
    def update_commands(self, filename: Optional[str]) -> None:
        """Update displayed commands for the given filename"""
        # Only update if in download mode
        if self.mode != "download":
            return
        
        self.current_filename = filename
        
        if not filename:
            self.update("No file selected")
            return
        
        commands = CommandGenerator.generate_commands(self.ip, self.port, filename)
        
        content = f"""[bold cyan]{filename}[/bold cyan]
{commands['url']}

{commands['wget']}
{commands['iwr_short']}
{commands['iwr_full']}
{commands['certutil']}"""
        
        self.update(content)
    
    def show_upload_commands(self, filename: str) -> None:
        """Switch to upload mode and show upload commands"""
        self.mode = "upload"
        self.upload_filename = filename
        commands = CommandGenerator.generate_upload_commands(self.ip, self.port, filename)
        
        content = f"""[bold cyan]{filename}[/bold cyan]
[dim](Upload Mode - Press Esc to return)[/dim]

{commands['curl_put']}
{commands['curl_post']}
{commands['wget_put']}
{commands['wget_post']}
{commands['ps_put']}
{commands['ps_post']}"""
        
        self.update(content)
    
    def show_download_commands(self) -> None:
        """Switch back to download mode"""
        self.mode = "download"
        self.update_commands(self.current_filename)


# ============================================================================
# Input Screen for Upload Filename
# ============================================================================

class FilenameInputScreen(ModalScreen):
    """Modal screen to input filename for upload commands"""
    
    CSS = """
    FilenameInputScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.8);
    }
    
    #input-dialog {
        width: 50;
        height: auto;
        background: black;
        border: solid white;
        padding: 1 2;
    }
    
    Label {
        color: white;
        margin-bottom: 1;
    }
    
    Input {
        width: 100%;
        height: 3;
        color: white;
        background: black;
        border: solid white;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Container(id="input-dialog"):
            yield Label("Enter filename to upload:")
            yield Input(placeholder="example.txt", id="filename-input")
    
    def on_mount(self) -> None:
        """Focus the input when mounted"""
        self.query_one(Input).focus()
    
    def on_input_submitted(self, event) -> None:
        """Handle Enter key - submit the filename"""
        filename = event.value.strip()
        if filename:
            self.dismiss(filename)
        else:
            self.dismiss(None)
    
    def on_key(self, event) -> None:
        """Handle Escape key - cancel input"""
        if event.key == "escape":
            self.dismiss(None)


# ============================================================================
# Main TUI Application
# ============================================================================

class UploadServerApp(App):
    """Interactive TUI for HTTP Upload/Download Server"""
    
    CSS = """
    Screen {
        layout: vertical;
    }
    
    FileBrowser {
        height: 60%;
        border: solid $primary;
        padding: 1;
    }
    
    CommandsPanel {
        height: 40%;
        border: solid $secondary;
        padding: 1;
        overflow-y: auto;
    }
    
    DataTable {
        height: 100%;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("r", "refresh", "Refresh", priority=True),
        Binding("u", "upload_mode", "Upload", priority=True),
        Binding("escape", "return_to_download", "Back", show=False),
    ]
    
    def __init__(self, ip: str, port: int, base_dir: str):
        super().__init__()
        self.ip = ip
        self.port = port
        self.base_dir = base_dir
        self.file_model = FileListModel(base_dir)
        self.file_browser = None
        self.commands_panel = None
        self.title = f"Upload Server - {ip}:{port}"
        self.sub_title = f"Serving: {os.path.abspath(base_dir)}"
    
    def compose(self) -> ComposeResult:
        """Create the UI layout"""
        yield Header()
        self.file_browser = FileBrowser(self.file_model, id="file-browser")
        self.commands_panel = CommandsPanel(self.ip, self.port, id="commands-panel")
        yield self.file_browser
        yield self.commands_panel
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize app and set up auto-refresh"""
        self.set_interval(1.0, self.auto_refresh)
        self.update_commands()
    
    def auto_refresh(self) -> None:
        """Automatically refresh file list every second"""
        self.file_browser.refresh_files()
        self.update_commands()
    
    def action_refresh(self) -> None:
        """Manual refresh action"""
        self.file_browser.refresh_files()
        self.update_commands()
    
    def action_upload_mode(self) -> None:
        """Prompt for filename and show upload commands"""
        self.push_screen(FilenameInputScreen(), self.handle_filename_input)
    
    def handle_filename_input(self, filename: Optional[str]) -> None:
        """Handle the filename input from dialog"""
        if filename:
            self.commands_panel.show_upload_commands(filename)
    
    def action_return_to_download(self) -> None:
        """Return to download commands view"""
        if self.commands_panel.mode == "upload":
            self.commands_panel.show_download_commands()
    
    def on_data_table_row_highlighted(self, event) -> None:
        """Handle row selection changes in the file browser"""
        self.update_commands()
    
    def update_commands(self) -> None:
        """Update the commands panel with current selection"""
        selected_file = self.file_browser.get_selected_file()
        self.commands_panel.update_commands(selected_file)
    
    def action_quit(self) -> None:
        """Quit the application"""
        self.exit()


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point - parse arguments and launch server + TUI"""
    parser = argparse.ArgumentParser(
        description="Interactive TUI HTTP Upload/Download Server",
        epilog="Press 'q' to quit, 'r' to refresh, Up/Down to navigate files"
    )
    parser.add_argument('port', type=int, help="Port number to listen on")
    parser.add_argument('path', nargs='?', default='.', 
                       help="Base directory for file operations (default: current directory)")
    parser.add_argument('--ip', type=str, 
                       help="IP address of the server (if omitted, attempts to use tun0 IP address)")
    
    args = parser.parse_args()
    
    port = args.port
    base_dir = os.path.abspath(args.path)
    ip = args.ip if args.ip else get_tun0_ip()

    # Validate IP address
    if not ip:
        print("Error: Could not get IP address for tun0 interface.")
        print("Please specify an IP address manually using --ip <ip_address>")
        sys.exit(1)
    
    # Validate base directory
    if not os.path.exists(base_dir):
        print(f"Error: Directory does not exist: {base_dir}")
        sys.exit(1)
    
    if not os.path.isdir(base_dir):
        print(f"Error: Path is not a directory: {base_dir}")
        sys.exit(1)
    
    # Start HTTP server in background thread
    server_thread = threading.Thread(
        target=run_server, 
        args=(port, base_dir), 
        daemon=True
    )
    server_thread.start()
    
    # Launch TUI application
    try:
        app = UploadServerApp(ip, port, base_dir)
        app.run()
    except Exception as e:
        print(f"Error starting TUI: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
