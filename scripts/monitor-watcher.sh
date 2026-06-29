#!/usr/bin/env bash
# Watches Hyprland events for monitor connect/disconnect.
# Auto-pops monitor-menu when HDMI is plugged in.

LOCK="/tmp/monitor-watcher.lock"

if [ -f "$LOCK" ]; then
    OLD_PID=$(cat "$LOCK" 2>/dev/null)
    if kill -0 "$OLD_PID" 2>/dev/null; then
        exit 0
    fi
fi
echo $$ > "$LOCK"
cleanup() { rm -f "$LOCK"; }
trap cleanup EXIT

exec python3 - <<'PYEOF'
import socket
import os
import subprocess
import time
import sys

def find_socket():
    sig = os.environ.get('HYPRLAND_INSTANCE_SIGNATURE', '')
    base = f'/run/user/{os.getuid()}/hypr'
    if sig:
        path = f'{base}/{sig}/.socket2.sock'
        if os.path.exists(path):
            return path
    # discover
    for _ in range(30):
        try:
            entries = os.listdir(base)
            for entry in entries:
                p = f'{base}/{entry}/.socket2.sock'
                if os.path.exists(p):
                    return p
        except Exception:
            pass
        time.sleep(1)
    return None

sock_path = find_socket()
if not sock_path:
    print('monitor-watcher: no hyprland socket found', file=sys.stderr)
    sys.exit(1)

print(f'monitor-watcher: listening on {sock_path}', flush=True)

while True:
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(sock_path)
        buf = b''
        while True:
            data = s.recv(4096)
            if not data:
                break
            buf += data
            while b'\n' in buf:
                line, buf = buf.split(b'\n', 1)
                event = line.decode('utf-8', errors='replace').strip()
                if event.startswith('monitoradded') or event.startswith('monitorremoved'):
                    print(f'monitor-watcher: {event}', flush=True)
                    time.sleep(1.2)
                    subprocess.Popen([os.path.expanduser('~/.local/bin/monitor-menu')])
        s.close()
    except Exception as e:
        print(f'monitor-watcher: reconnecting ({e})', flush=True)
        time.sleep(2)
PYEOF
