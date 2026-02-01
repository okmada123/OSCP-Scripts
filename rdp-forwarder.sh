#!/bin/bash

# Default ports
LPORT=3389
DPORT=3389

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --lport)
            LPORT="$2"
            shift 2
            ;;
        --dport)
            DPORT="$2"
            shift 2
            ;;
        *)
            # First positional argument is the IP
            if [[ -z "$IP" ]]; then
                IP="$1"
                shift
            else
                echo "Error: Unknown argument: $1"
                exit 1
            fi
            ;;
    esac
done

# Check if IP is provided
if [[ -z "$IP" ]]; then
    echo "Usage: $0 <ip_address> [--lport <port>] [--dport <port>]"
    echo "  <ip_address>     Target IP address (required)"
    echo "  --lport <port>   Local port to listen on (default: 3389)"
    echo "  --dport <port>   Destination port to forward to (default: 3389)"
    exit 1
fi

# Build the command
CMD="socat -d TCP-LISTEN:${LPORT},fork TCP:${IP}:${DPORT}"

# Echo info about what is starting
echo "Starting: ${CMD}"
echo ""

# Run the command
$CMD
