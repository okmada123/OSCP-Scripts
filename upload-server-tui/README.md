# Upload Server TUI

Interactive Terminal UI for HTTP Upload/Download Server with live file browsing and command generation.

## Features

- **Top Pane**: File browser showing all files in the served directory with size and modification time
- **Bottom Pane**: Download commands for the selected file (wget, PowerShell, certutil)
- **Auto-refresh**: File list updates every 3 seconds automatically
- **Keyboard Navigation**:
  - `Up/Down`: Navigate through files
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
2. The TUI displays all files in the served directory
3. Select a file with arrow keys to see download commands
4. Commands update automatically as you navigate
5. The file list refreshes every 3 seconds to show new files

## Server Endpoints

- **GET** `/filename`: Download a file
- **PUT** `/filename`: Upload a file (overwrites if exists)
- **POST** `/filename`: Upload a file (same as PUT)
