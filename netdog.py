#!/usr/bin/env python3

"""
safe_nc.py

A lightweight netcat-style networking utility written in Python.

Features
--------
- Client mode for connecting to remote hosts
- Listener mode for accepting inbound TCP connections
- Interactive message exchange
- File upload capability
- Optional local command execution on startup

"""

import argparse
import os
import socket
import subprocess
import threading

BUFFER = 4096


def receive(sock):
    """Continuously receive data from a socket."""
    try:
        while True:
            data = sock.recv(BUFFER)
            if not data:
                break
            print(data.decode(errors="ignore"), end="")
    except:
        pass


def send_input(sock):
    """Send user input to the socket."""
    try:
        while True:
            msg = input()
            sock.send((msg + "\n").encode())
    except KeyboardInterrupt:
        sock.close()


def upload_file(sock, filepath):
    """Upload a file to the connected peer."""
    if not os.path.isfile(filepath):
        print(f"[!] File not found: {filepath}")
        return

    filename = os.path.basename(filepath)
    filesize = os.path.getsize(filepath)

    header = f"UPLOAD {filename} {filesize}\n"
    sock.send(header.encode())

    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(BUFFER)
            if not chunk:
                break
            sock.send(chunk)

    print(f"[+] Uploaded {filename} ({filesize} bytes)")


def handle_upload(sock, header):
    """Receive uploaded file."""
    _, filename, size = header.split()
    size = int(size)

    out = f"received_{filename}"
    remaining = size

    with open(out, "wb") as f:
        while remaining > 0:
            chunk = sock.recv(min(BUFFER, remaining))
            if not chunk:
                break
            f.write(chunk)
            remaining -= len(chunk)

    print(f"\n[+] File saved as {out}")


def receive_loop(sock):
    """Receive messages and detect upload protocol."""
    while True:
        data = sock.recv(BUFFER)
        if not data:
            break

        text = data.decode(errors="ignore")

        if text.startswith("UPLOAD"):
            handle_upload(sock, text.strip())
        else:
            print(text, end="")


def run_local_command(cmd):
    """Execute a local command when the program starts."""
    try:
        print(f"[+] Running startup command: {cmd}")
        subprocess.run(cmd, shell=True)
    except Exception as e:
        print(f"[!] Command failed: {e}")


def client(target, port, upload=None, command=None):
    """Connect to remote server."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((target, port))

    print(f"[+] Connected to {target}:{port}")

    if command:
        run_local_command(command)

    thread = threading.Thread(target=receive_loop, args=(sock,), daemon=True)
    thread.start()

    if upload:
        upload_file(sock, upload)

    send_input(sock)


def handle_client(sock, addr):
    """Handle inbound client connection."""
    print(f"[+] Connection from {addr[0]}:{addr[1]}")

    thread = threading.Thread(target=receive_loop, args=(sock,), daemon=True)
    thread.start()

    send_input(sock)


def listener(port, host):
    """Start listening server."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(5)

    print(f"[+] Listening on {host}:{port}")

    while True:
        client_sock, addr = server.accept()
        threading.Thread(
            target=handle_client,
            args=(client_sock, addr),
            daemon=True
        ).start()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Python netcat-style utility for TCP connections and file transfer."
    )

    parser.add_argument(
        "-l", "--listen",
        action="store_true",
        help="Listen mode (wait for inbound connections)"
    )

    parser.add_argument(
        "-p", "--port",
        type=int,
        required=True,
        help="Port number to connect to or listen on"
    )

    parser.add_argument(
        "-t", "--target",
        default="127.0.0.1",
        help="Target host (default: 127.0.0.1)"
    )

    parser.add_argument(
        "-upload",
        metavar="FILE",
        help="Upload a file after connecting"
    )

    parser.add_argument(
        "-c", "--command",
        metavar="CMD",
        help="Run a local command when the program starts"
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if args.listen:
        listener(args.port, args.target)
    else:
        client(args.target, args.port, args.upload, args.command)


if __name__ == "__main__":
    main()
