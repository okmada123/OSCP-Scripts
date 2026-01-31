# x41 OSCP Scripts

upload-server.py
- inspired by [https://github.com/yaldobaoth/OSCP-Scripts](https://github.com/yaldobaoth/OSCP-Scripts/blob/main/scripts/upload-server) - thanks
- interactive interface is vibe-coded
- **DO NOT** expose it to an untrusted network.

reverse-generator-windows.py
- dynamically grabs tun0 IP address
- uses msfvenom reverse shell generator
- supports 2 scenarios:
  - plain reverse.exe
  - reverse.exe + DLL to trigger reverse.exe (For DLL Hijacking)
