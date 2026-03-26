from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Any


class FaultInjectionError(Exception):
    pass


def is_port_open(host: str, port: int, timeout_s: float = 1.0) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout_s)
    try:
        sock.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        sock.close()


def wait_port_open(host: str, port: int, timeout_s: int = 60, interval_s: float = 1.0) -> None:
    start = time.time()
    while time.time() - start < timeout_s:
        if is_port_open(host, port):
            return
        time.sleep(interval_s)
    raise TimeoutError(f"Port did not open in time: {host}:{port}")


def wait_port_closed(host: str, port: int, timeout_s: int = 30, interval_s: float = 1.0) -> None:
    start = time.time()
    while time.time() - start < timeout_s:
        if not is_port_open(host, port):
            return
        time.sleep(interval_s)
    raise TimeoutError(f"Port did not close in time: {host}:{port}")


def find_pid_by_port(port: int) -> int | None:
    """
    Windows:
      netstat -ano | findstr :19193
    解析 LISTENING 对应 PID
    """
    command = ["cmd", "/c", f'netstat -ano | findstr :{port}']
    result = subprocess.run(command, capture_output=True, text=True, check=False)

    if result.returncode not in (0, 1):
        raise FaultInjectionError(f"Failed to query port {port}: {result.stderr}")

    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) < 5:
            continue

        proto = parts[0].upper()
        local_addr = parts[1]
        state = parts[3].upper() if len(parts) >= 5 else ""
        pid_str = parts[-1]

        if proto == "TCP" and local_addr.endswith(f":{port}") and state == "LISTENING" and pid_str.isdigit():
            return int(pid_str)

    return None


def kill_process(pid: int) -> None:
    command = ["taskkill", "/PID", str(pid), "/F"]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise FaultInjectionError(f"Failed to kill pid={pid}: {result.stderr}")


def start_java_process(
    command: str,
    workdir: str | None = None,
) -> int:
    """
    直接启动 bat/cmd，不做额外 shell 拼接。
    command 现在建议传一个 bat 文件的绝对路径。
    """
    cwd = Path(workdir).resolve() if workdir else None

    process = subprocess.Popen(
        command,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=True,
    )
    return process.pid



def restart_process_by_port(
    port: int,
    start_command: str,
    host: str = "localhost",
    down_timeout_s: int = 30,
    up_timeout_s: int = 120,
    workdir: str | None = None,
) -> dict[str, Any]:
    old_pid = find_pid_by_port(port)
    if old_pid is None:
        raise FaultInjectionError(f"No LISTENING process found on port {port}")

    kill_process(old_pid)
    wait_port_closed(host, port, timeout_s=down_timeout_s)

    start_ts = time.time()
    new_pid = start_java_process(start_command, workdir=workdir)
    wait_port_open(host, port, timeout_s=up_timeout_s)
    recovery_time_s = time.time() - start_ts

    actual_pid = find_pid_by_port(port)

    return {
        "killed_pid": old_pid,
        "new_pid": new_pid,
        "listening_pid": actual_pid,
        "recovery_time_s": round(recovery_time_s, 6),
    }
