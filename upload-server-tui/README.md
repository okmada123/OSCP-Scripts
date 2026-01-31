# Upload Server TUI

Interactive Terminal UI for HTTP Upload/Download Server with live file browsing and command generation.

## Features

- **Top Pane**: File browser showing all files in the served directory with size and modification time
- **Bottom Pane**: Download/upload commands for the selected file
- **Auto-refresh**: File list updates every second automatically
- **Uploads Directory**: All uploaded files are automatically saved to `uploads/` subdirectory
- **Keyboard Navigation**:
  - `Up/Down`: Navigate through files
  - `u`: Generate upload commands for a filename
  - `Esc`: Return to download commands view
  - `r`: Manual refresh
  - `q`: Quit application

## Installation

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# Using venv
.venv/bin/python upload-server.py <port> [path] [--ip <ip>]

# Examples
.venv/bin/python upload-server.py 8000
.venv/bin/python upload-server.py 8000 /tmp/shared
.venv/bin/python upload-server.py 8000 . --ip 10.10.14.5
```

## Arguments

- `port`: Port number to listen on (required)
- `path`: Base directory to serve files from (default: current directory)
- `--ip`: IP address to use in commands (default: auto-detect from tun0 interface)

## How It Works

1. The HTTP server runs in a background thread, accepting GET/PUT/POST requests
2. An `uploads/` directory is automatically created in the served directory
3. The TUI displays files from both the base directory and `uploads/` subdirectory
4. Select a file with arrow keys to see download commands
5. Press `u` to generate upload commands for a specific filename
6. Commands update automatically as you navigate
7. The file list refreshes every second to show new files

## Server Endpoints

- **GET** `/filename`: Download a file from base directory
- **GET** `/uploads/filename`: Download a file from uploads directory
- **PUT** `/filename`: Upload a file (saved to `uploads/` directory)
- **POST** `/filename`: Upload a file (saved to `uploads/` directory)

## Uploads Directory

All files uploaded via PUT/POST requests are automatically saved to the `uploads/` subdirectory within the served directory. This keeps uploaded files organized and separate from your original files. Files in the uploads directory are shown in the file browser with the `uploads/` prefix.
