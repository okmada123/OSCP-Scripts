#!/usr/bin/env python3

import os
import sys
import shutil
import subprocess

# Color codes
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'
BOLD = '\033[1m'

TARGET_DIR = "/usr/bin/"
SKIP_FILES = [".md", "install.py"]

def get_script_directory():
    """Get the directory where this script is located."""
    return os.path.dirname(os.path.abspath(__file__))

def should_skip_file(filename):
    """Check if a file should be skipped based on skip patterns (case-insensitive)."""
    filename_lower = filename.lower()
    for pattern in SKIP_FILES:
        if filename == pattern or filename_lower.endswith(pattern.lower()):
            return True
    return False

def get_files_to_install(directory):
    """Get list of files to install, excluding skipped files and directories."""
    files_to_install = []
    
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        
        # Skip directories
        if os.path.isdir(item_path):
            continue
        
        # Skip files matching skip patterns
        if should_skip_file(item):
            continue
        
        files_to_install.append(item)
    
    return files_to_install

def check_existing_files(files, target_dir):
    """Check which files already exist in the target directory."""
    existing_files = []
    
    for filename in files:
        target_path = os.path.join(target_dir, filename)
        if os.path.exists(target_path):
            existing_files.append(filename)
    
    return existing_files

def prompt_user_confirmation(files_to_install, existing_files):
    """Prompt user for confirmation before installing."""
    print(f"\n{'='*60}")
    print(f"Files to be installed to {CYAN}{TARGET_DIR}{RESET}:")
    print(f"{'='*60}")
    
    for filename in files_to_install:
        if filename in existing_files:
            status = f" {YELLOW}[WILL OVERWRITE]{RESET}"
        else:
            status = f" {GREEN}[NEW]{RESET}"
        print(f"  - {filename}{status}")
    
    print(f"{'='*60}")
    
    if existing_files:
        print(f"\n{YELLOW}{BOLD}WARNING:{RESET} {len(existing_files)} file(s) will be overwritten:")
        for filename in existing_files:
            print(f"  - {YELLOW}{filename}{RESET}")
    
    print(f"\nTotal files to install: {BOLD}{len(files_to_install)}{RESET}")
    
    response = input(f"\n{BOLD}Do you want to proceed with the installation? (yes/no):{RESET} ").strip().lower()
    return response in ['yes', 'y']

def install_files(source_dir, files, target_dir):
    """Install files to target directory with elevated privileges."""
    # Check if we're already running as root
    if os.geteuid() == 0:
        # Already root, copy directly
        for filename in files:
            source_path = os.path.join(source_dir, filename)
            target_path = os.path.join(target_dir, filename)
            try:
                shutil.copy2(source_path, target_path)
                os.chmod(target_path, 0o755)  # Make executable
                print(f"{GREEN}[OK]{RESET} Installed: {filename}")
            except Exception as e:
                print(f"{RED}[ERROR]{RESET} Failed to install {filename}: {e}")
                return False
        return True
    else:
        # Need to use sudo
        print(f"\n{CYAN}Elevating privileges (you may be prompted for your password)...{RESET}")
        
        for filename in files:
            source_path = os.path.join(source_dir, filename)
            target_path = os.path.join(target_dir, filename)
            
            try:
                # Copy file using sudo
                subprocess.run(['sudo', 'cp', source_path, target_path], check=True)
                # Make executable using sudo
                subprocess.run(['sudo', 'chmod', '755', target_path], check=True)
                print(f"{GREEN}[OK]{RESET} Installed: {filename}")
            except subprocess.CalledProcessError as e:
                print(f"{RED}[ERROR]{RESET} Failed to install {filename}: {e}")
                return False
        
        return True

def main():
    print(f"\n{BOLD}{CYAN}{'='*60}")
    print(f"OSCP Scripts Installer")
    print(f"{'='*60}{RESET}")
    
    # Get script directory and use it as working directory
    script_dir = get_script_directory()
    os.chdir(script_dir)
    print(f"Working directory: {BLUE}{script_dir}{RESET}")
    
    # Get list of files to install
    files_to_install = get_files_to_install(script_dir)
    
    if not files_to_install:
        print(f"\n{YELLOW}No files found to install.{RESET}")
        sys.exit(0)
    
    # Check for existing files
    existing_files = check_existing_files(files_to_install, TARGET_DIR)
    
    # Prompt user for confirmation
    if not prompt_user_confirmation(files_to_install, existing_files):
        print(f"\n{RED}Installation cancelled by user.{RESET}")
        sys.exit(0)
    
    # Install files
    print(f"\n{'='*60}")
    print(f"{BOLD}Installing files...{RESET}")
    print(f"{'='*60}")
    
    if install_files(script_dir, files_to_install, TARGET_DIR):
        print(f"\n{GREEN}{BOLD}{'='*60}")
        print(f"Installation completed successfully!")
        print(f"{'='*60}{RESET}")
        sys.exit(0)
    else:
        print(f"\n{RED}{BOLD}{'='*60}")
        print(f"Installation failed.")
        print(f"{'='*60}{RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()