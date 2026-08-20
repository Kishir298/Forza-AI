import json
import os
import platform
import re
import shutil
import subprocess
import time
from pathlib import Path

import psutil


def _safe_call(function, default=None):
    try:
        return function()
    except (
        psutil.NoSuchProcess,
        psutil.AccessDenied,
        psutil.ZombieProcess,
        OSError,
        ValueError,
    ):
        return default


def _run_command(command, timeout=3):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

        if result.returncode != 0:
            return None

        output = result.stdout.strip()

        return output if output else None

    except (
        subprocess.TimeoutExpired,
        FileNotFoundError,
        OSError,
        ValueError,
    ):
        return None


def _format_uptime(seconds):
    if seconds is None:
        return None

    try:
        seconds = max(0, int(seconds))
    except (TypeError, ValueError):
        return None

    days = seconds // 86400
    seconds %= 86400

    hours = seconds // 3600
    seconds %= 3600

    minutes = seconds // 60
    seconds %= 60

    if days:
        return f"{days}d {hours}h {minutes}m {seconds}s"

    if hours:
        return f"{hours}h {minutes}m {seconds}s"

    if minutes:
        return f"{minutes}m {seconds}s"

    return f"{seconds}s"


def _empty_network(source=None):
    return {
        "available": False,
        "bytes_sent": None,
        "bytes_received": None,
        "bytes_sent_per_sec": None,
        "bytes_received_per_sec": None,
        "byte_counters_available": False,
        "connection_count": 0,
        "connections": [],
        "source": source,
    }


def _normalise_connection(connection):
    local_address = getattr(
        connection,
        "laddr",
        None,
    )

    remote_address = getattr(
        connection,
        "raddr",
        None,
    )

    if hasattr(local_address, "ip"):
        local_ip = local_address.ip
        local_port = local_address.port
    elif isinstance(local_address, tuple):
        local_ip = (
            local_address[0]
            if local_address
            else None
        )
        local_port = (
            local_address[1]
            if len(local_address) > 1
            else None
        )
    else:
        local_ip = None
        local_port = None

    if hasattr(remote_address, "ip"):
        remote_ip = remote_address.ip
        remote_port = remote_address.port
    elif isinstance(remote_address, tuple):
        remote_ip = (
            remote_address[0]
            if remote_address
            else None
        )
        remote_port = (
            remote_address[1]
            if len(remote_address) > 1
            else None
        )
    else:
        remote_ip = None
        remote_port = None

    return {
        "local_address": local_ip,
        "local_port": local_port,
        "remote_address": remote_ip,
        "remote_port": remote_port,
        "state": getattr(
            connection,
            "status",
            None,
        ),
        "family": str(
            getattr(
                connection,
                "family",
                "",
            )
        ),
        "type": str(
            getattr(
                connection,
                "type",
                "",
            )
        ),
    }


def _collect_network_connections():
    """
    Cross-platform process-to-network connection mapping.

    psutil.net_connections() is used on Windows, Linux,
    macOS, and other platforms supported by psutil.

    The owning PID is not guaranteed to be available on
    every operating system or for every connection. Such
    connections are skipped rather than assigned incorrectly.
    """

    grouped = {}

    try:
        connections = psutil.net_connections(
            kind="inet"
        )
    except (
        psutil.AccessDenied,
        OSError,
        NotImplementedError,
    ):
        connections = []

    for connection in connections:
        pid = getattr(
            connection,
            "pid",
            None,
        )

        if pid is None:
            continue

        try:
            pid = int(pid)
        except (
            TypeError,
            ValueError,
        ):
            continue

        if pid not in grouped:
            grouped[pid] = {
                "available": True,
                "bytes_sent": None,
                "bytes_received": None,
                "bytes_sent_per_sec": None,
                "bytes_received_per_sec": None,
                "byte_counters_available": False,
                "connection_count": 0,
                "connections": [],
                "source": "psutil network connections",
            }

        grouped[pid]["connections"].append(
            _normalise_connection(
                connection
            )
        )

        grouped[pid]["connection_count"] += 1

    return grouped


def _parse_nethogs_output(output):
    """
    Parse text-mode nethogs output.

    nethogs is optional on Linux. Different distributions
    can expose slightly different formatting, so parsing is
    deliberately defensive.

    The resulting rates are bytes/sec.
    """

    grouped = {}

    if not output:
        return grouped

    for line in output.splitlines():
        line = line.strip()

        if not line:
            continue

        lowered = line.lower()

        if (
            lowered.startswith("waiting")
            or lowered.startswith("refreshing")
            or lowered.startswith("pid")
            or lowered.startswith("net hogs")
        ):
            continue

        parts = re.split(
            r"\s+",
            line,
        )

        if len(parts) < 3:
            continue

        pid = None

        for part in parts:
            match = re.search(
                r"/(\d+)/",
                part,
            )

            if match:
                try:
                    pid = int(
                        match.group(1)
                    )
                except ValueError:
                    pid = None

                break

            if "/" in part:
                match = re.search(
                    r"(\d+)$",
                    part,
                )

                if match:
                    try:
                        pid = int(
                            match.group(1)
                        )
                    except ValueError:
                        pid = None

                    break

        if pid is None:
            continue

        rate_values = []

        for part in parts:
            cleaned = (
                part.replace(
                    "KB/s",
                    "",
                )
                .replace(
                    "kB/s",
                    "",
                )
                .replace(
                    "kb/s",
                    "",
                )
                .replace(
                    "MB/s",
                    "",
                )
                .replace(
                    "MB",
                    "",
                )
                .replace(
                    "KB",
                    "",
                )
                .replace(
                    "kB",
                    "",
                )
            )

            try:
                value = float(
                    cleaned
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            rate_values.append(
                value
            )

        if len(rate_values) < 2:
            continue

        sent = rate_values[-2]
        received = rate_values[-1]

        # nethogs normally reports KB/s.
        sent_per_sec = max(
            0.0,
            sent,
        ) * 1024

        received_per_sec = max(
            0.0,
            received,
        ) * 1024

        grouped[pid] = {
            "bytes_sent": None,
            "bytes_received": None,
            "bytes_sent_per_sec": round(
                sent_per_sec,
                2,
            ),
            "bytes_received_per_sec": round(
                received_per_sec,
                2,
            ),
            "byte_counters_available": True,
            "source": "Linux nethogs",
        }

    return grouped


def _collect_linux_network_counters():
    """
    Optional Linux process network telemetry.

    Uses nethogs when installed.

    If nethogs is unavailable, the caller still receives
    cross-platform psutil connection information.
    """

    if platform.system() != "Linux":
        return {}

    nethogs = shutil.which(
        "nethogs"
    )

    if not nethogs:
        return {}

    output = _run_command(
        [
            nethogs,
            "-t",
            "-c",
            "1",
        ],
        timeout=5,
    )

    if not output:
        return {}

    return _parse_nethogs_output(
        output
    )


def _parse_nettop_output(output):
    """
    Best-effort parser for macOS nettop batch output.

    nettop output varies between macOS versions. This parser
    therefore only accepts rows where a PID and two usable
    numeric traffic values can be identified.

    Rates are returned as bytes/sec when detected.
    """

    grouped = {}

    if not output:
        return grouped

    for line in output.splitlines():
        line = line.strip()

        if not line:
            continue

        lowered = line.lower()

        if (
            lowered.startswith("time,")
            or lowered.startswith("interface")
            or lowered.startswith("process")
        ):
            continue

        parts = [
            part.strip()
            for part in line.split(",")
        ]

        if len(parts) < 3:
            continue

        pid = None

        # nettop normally contains a PID column.
        for part in parts:
            try:
                candidate = int(
                    part
                )

                if candidate > 0:
                    pid = candidate
                    break

            except (
                TypeError,
                ValueError,
            ):
                continue

        if pid is None:
            continue

        numeric_values = []

        for part in parts:
            cleaned = (
                part.replace(
                    "B",
                    "",
                )
                .replace(
                    "/s",
                    "",
                )
                .replace(
                    "K",
                    "",
                )
                .replace(
                    "M",
                    "",
                )
                .replace(
                    "G",
                    "",
                )
            )

            try:
                numeric_values.append(
                    float(
                        cleaned
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

        if len(numeric_values) < 2:
            continue

        sent_per_sec = max(
            0.0,
            numeric_values[-2],
        )

        received_per_sec = max(
            0.0,
            numeric_values[-1],
        )

        grouped[pid] = {
            "bytes_sent": None,
            "bytes_received": None,
            "bytes_sent_per_sec": round(
                sent_per_sec,
                2,
            ),
            "bytes_received_per_sec": round(
                received_per_sec,
                2,
            ),
            "byte_counters_available": True,
            "source": "macOS nettop",
        }

    return grouped


def _collect_macos_network_counters():
    """
    Optional macOS process network telemetry.

    Uses nettop when available.

    If nettop is unavailable or its output cannot be
    interpreted safely, psutil connection information
    remains available.
    """

    if platform.system() != "Darwin":
        return {}

    nettop = shutil.which(
        "nettop"
    )

    if not nettop:
        return {}

    output = _run_command(
        [
            nettop,
            "-P",
            "-L",
            "1",
            "-x",
            "-n",
        ],
        timeout=5,
    )

    if not output:
        return {}

    return _parse_nettop_output(
        output
    )


def _collect_network_counters():
    """
    Collect optional per-process network traffic rates.

    Platform strategy:

    Linux:
        nethogs when available.

    macOS:
        nettop when available.

    Windows:
        No fabricated network byte counters. Windows
        process-level network byte accounting is not exposed
        consistently through psutil.

    All platforms still receive connection information from
    psutil.net_connections().
    """

    system = platform.system()

    if system == "Linux":
        return _collect_linux_network_counters()

    if system == "Darwin":
        return _collect_macos_network_counters()

    return {}


def _collect_windows_gpu():
    grouped = {}

    if platform.system() != "Windows":
        return grouped

    powershell = shutil.which(
        "powershell.exe"
    )

    if not powershell:
        return grouped

    script = (
        "$ErrorActionPreference='SilentlyContinue'; "
        "$counter=Get-Counter "
        "'\\GPU Engine(*)\\Utilization Percentage' "
        "-ErrorAction SilentlyContinue; "
        "if($null -eq $counter){exit 1}; "
        "$counter.CounterSamples | "
        "Select-Object InstanceName,CookedValue | "
        "ConvertTo-Json -Compress"
    )

    output = _run_command(
        [
            powershell,
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            script,
        ],
        timeout=8,
    )

    if not output:
        return grouped

    try:
        data = json.loads(
            output
        )
    except (
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ):
        return grouped

    if isinstance(
        data,
        dict,
    ):
        data = [data]

    for item in data:
        if not isinstance(
            item,
            dict,
        ):
            continue

        instance_name = str(
            item.get(
                "InstanceName",
                "",
            )
        )

        marker = "pid_"

        marker_index = (
            instance_name.lower().find(
                marker
            )
        )

        if marker_index == -1:
            continue

        pid_start = (
            marker_index
            + len(marker)
        )

        pid_chars = []

        for character in instance_name[
            pid_start:
        ]:
            if character.isdigit():
                pid_chars.append(
                    character
                )
            else:
                break

        if not pid_chars:
            continue

        try:
            pid = int(
                "".join(
                    pid_chars
                )
            )

            usage = max(
                0.0,
                float(
                    item.get(
                        "CookedValue",
                        0,
                    )
                ),
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        if pid not in grouped:
            grouped[pid] = {
                "available": True,
                "usage_percent": 0.0,
                "engine_count": 0,
                "source": (
                    "Windows GPU Engine"
                ),
            }

        grouped[pid][
            "usage_percent"
        ] += usage

        grouped[pid][
            "engine_count"
        ] += 1

    for data in grouped.values():
        data[
            "usage_percent"
        ] = round(
            min(
                100.0,
                data[
                    "usage_percent"
                ],
            ),
            1,
        )

    return grouped


def _collect_linux_gpu():
    """
    Linux GPU process utilisation is not exposed through one
    universal standard interface.

    Keep this backend separate so future GPU providers can be
    added without making the process collector Linux-only.
    """

    if platform.system() != "Linux":
        return {}

    drm_path = Path(
        "/sys/class/drm"
    )

    if not drm_path.exists():
        return {}

    # Detect GPU devices, but do not incorrectly claim that
    # they provide process-level utilisation.
    for entry in drm_path.glob(
        "card*"
    ):
        if "-" in entry.name:
            continue

        device_path = (
            entry / "device"
        )

        if device_path.exists():
            return {}

    return {}


def _collect_macos_gpu():
    """
    macOS does not provide one universally available,
    process-level GPU utilisation API.

    Return an empty mapping rather than inventing telemetry.
    """

    if platform.system() != "Darwin":
        return {}

    return {}


def _collect_gpu_data():
    system = platform.system()

    if system == "Windows":
        return _collect_windows_gpu()

    if system == "Linux":
        return _collect_linux_gpu()

    if system == "Darwin":
        return _collect_macos_gpu()

    return {}


def _get_memory(process):
    memory_percent = _safe_call(
        process.memory_percent,
        0.0,
    )

    memory_info = _safe_call(
        process.memory_info,
        None,
    )

    rss_bytes = None

    if memory_info is not None:
        rss_bytes = getattr(
            memory_info,
            "rss",
            None,
        )

    try:
        memory_percent = round(
            float(
                memory_percent or 0
            ),
            2,
        )
    except (
        TypeError,
        ValueError,
    ):
        memory_percent = 0.0

    return {
        "memory_percent": memory_percent,
        "memory_bytes": (
            int(rss_bytes)
            if rss_bytes is not None
            else None
        ),
        "memory_mb": (
            round(
                rss_bytes
                / (1024 ** 2),
                2,
            )
            if rss_bytes is not None
            else None
        ),
    }


def _get_disk(process):
    io = _safe_call(
        process.io_counters,
        None,
    )

    if io is None:
        return {
            "available": False,
            "read_bytes": None,
            "write_bytes": None,
            "read_count": None,
            "write_count": None,
            "read_mb": None,
            "write_mb": None,
        }

    read_bytes = getattr(
        io,
        "read_bytes",
        None,
    )

    write_bytes = getattr(
        io,
        "write_bytes",
        None,
    )

    read_count = getattr(
        io,
        "read_count",
        None,
    )

    write_count = getattr(
        io,
        "write_count",
        None,
    )

    return {
        "available": (
            read_bytes is not None
            or write_bytes is not None
        ),
        "read_bytes": read_bytes,
        "write_bytes": write_bytes,
        "read_count": read_count,
        "write_count": write_count,
        "read_mb": (
            round(
                read_bytes
                / (1024 ** 2),
                2,
            )
            if read_bytes is not None
            else None
        ),
        "write_mb": (
            round(
                write_bytes
                / (1024 ** 2),
                2,
            )
            if write_bytes is not None
            else None
        ),
    }


def _get_uptime(process):
    create_time = _safe_call(
        process.create_time,
        None,
    )

    if create_time is None:
        return {
            "available": False,
            "start_time": None,
            "uptime_seconds": None,
            "uptime": None,
        }

    try:
        uptime_seconds = max(
            0.0,
            time.time()
            - float(
                create_time
            ),
        )

        return {
            "available": True,
            "start_time": float(
                create_time
            ),
            "uptime_seconds": round(
                uptime_seconds,
                1,
            ),
            "uptime": _format_uptime(
                uptime_seconds
            ),
        }

    except (
        TypeError,
        ValueError,
        OSError,
    ):
        return {
            "available": False,
            "start_time": None,
            "uptime_seconds": None,
            "uptime": None,
        }


def _is_real_executable_path(path):
    if not path:
        return False

    try:
        path_string = str(
            path
        )

        if not path_string:
            return False

        path_object = Path(
            path_string
        )

        if path_object.is_absolute():
            return True

        if (
            len(path_string) >= 3
            and path_string[1] == ":"
            and path_string[2]
            in ("\\", "/")
        ):
            return True

        if path_string.startswith(
            "\\\\"
        ):
            return True

        return False

    except (
        TypeError,
        ValueError,
        OSError,
    ):
        return False


def _get_path(process):
    executable = _safe_call(
        process.exe,
        None,
    )

    working_directory = _safe_call(
        process.cwd,
        None,
    )

    real_path = None

    if _is_real_executable_path(
        executable
    ):
        real_path = executable
    elif executable:
        try:
            executable_string = str(
                executable
            )

            if os.path.isabs(
                executable_string
            ):
                real_path = executable_string
        except (
            TypeError,
            ValueError,
            OSError,
        ):
            real_path = None

    return {
        "available": (
            real_path is not None
        ),
        "executable": real_path,
        "working_directory": (
            working_directory
        ),
    }


def _get_metadata(process):
    return {
        "username": _safe_call(
            process.username,
            None,
        ),
        "status": _safe_call(
            process.status,
            None,
        ),
        "thread_count": _safe_call(
            process.num_threads,
            None,
        ),
    }


def _build_network(
    pid,
    connection_data,
    counter_data,
):
    network = _empty_network()

    connection = connection_data.get(
        pid
    )

    if connection is not None:
        network.update(
            connection
        )

    counter = counter_data.get(
        pid
    )

    if counter is not None:
        # Only overwrite values that the counter provider
        # actually knows about.
        for field in (
            "bytes_sent",
            "bytes_received",
            "bytes_sent_per_sec",
            "bytes_received_per_sec",
        ):
            if field in counter:
                network[field] = (
                    counter[field]
                )

        if counter.get(
            "byte_counters_available",
            False,
        ):
            network[
                "byte_counters_available"
            ] = True

        counter_source = counter.get(
            "source"
        )

        if counter_source:
            if network.get(
                "source"
            ):
                network[
                    "source"
                ] = (
                    f"{network['source']}; "
                    f"{counter_source}"
                )
            else:
                network[
                    "source"
                ] = counter_source

        network[
            "available"
        ] = True

    elif connection is not None:
        network[
            "available"
        ] = True

    return network


def _build_gpu(
    pid,
    gpu_data,
):
    if pid in gpu_data:
        return gpu_data[pid]

    system = platform.system()

    if system == "Windows":
        return {
            "available": True,
            "usage_percent": 0.0,
            "engine_count": 0,
            "source": (
                "Windows GPU Engine"
            ),
        }

    if system == "Linux":
        return {
            "available": False,
            "usage_percent": None,
            "engine_count": 0,
            "source": (
                "Linux GPU process "
                "telemetry unavailable"
            ),
        }

    if system == "Darwin":
        return {
            "available": False,
            "usage_percent": None,
            "engine_count": 0,
            "source": (
                "macOS GPU process "
                "telemetry unavailable"
            ),
        }

    return {
        "available": False,
        "usage_percent": None,
        "engine_count": 0,
        "source": None,
    }


def _build_process(
    process,
    network_connections,
    network_counters,
    gpu_data,
):
    pid = _safe_call(
        lambda: process.pid,
        None,
    )

    if pid is None:
        return None

    name = _safe_call(
        process.name,
        "Unknown",
    )

    cpu_percent = _safe_call(
        lambda: process.cpu_percent(
            interval=None
        ),
        0.0,
    )

    try:
        cpu_percent = round(
            max(
                0.0,
                float(
                    cpu_percent or 0
                ),
            ),
            1,
        )
    except (
        TypeError,
        ValueError,
    ):
        cpu_percent = 0.0

    memory = _get_memory(
        process
    )

    disk = _get_disk(
        process
    )

    uptime = _get_uptime(
        process
    )

    path = _get_path(
        process
    )

    metadata = _get_metadata(
        process
    )

    network = _build_network(
        pid,
        network_connections,
        network_counters,
    )

    gpu = _build_gpu(
        pid,
        gpu_data,
    )

    return {
        "pid": pid,
        "name": (
            name or "Unknown"
        ),
        "cpu_percent": (
            cpu_percent
        ),
        "memory_percent": memory[
            "memory_percent"
        ],
        "memory_bytes": memory[
            "memory_bytes"
        ],
        "memory_mb": memory[
            "memory_mb"
        ],
        "path": path[
            "executable"
        ],
        "executable": path[
            "executable"
        ],
        "path_available": path[
            "available"
        ],
        "working_directory": path[
            "working_directory"
        ],
        "disk": disk,
        "network": network,
        "gpu": gpu,
        "uptime": uptime,
        "username": metadata[
            "username"
        ],
        "status": metadata[
            "status"
        ],
        "thread_count": metadata[
            "thread_count"
        ],
    }


def get_processes(limit=10):
    try:
        limit = int(
            limit
        )
    except (
        TypeError,
        ValueError,
    ):
        limit = 10

    limit = max(
        1,
        limit,
    )

    try:
        process_list = list(
            psutil.process_iter()
        )
    except Exception:
        process_list = []

    active_processes = []

    for process in process_list:
        try:
            process.cpu_percent(
                interval=None
            )

            active_processes.append(
                process
            )

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            continue

    # Short sampling interval so the collector doesn't
    # freeze the rest of the monitoring system.
    time.sleep(
        0.1
    )

    # Cross-platform network connections.
    network_connections = (
        _collect_network_connections()
    )

    # Optional platform-specific byte-rate providers.
    network_counters = (
        _collect_network_counters()
    )

    # Optional GPU backend.
    gpu_data = (
        _collect_gpu_data()
    )

    processes = []

    for process in active_processes:
        try:
            process_info = _build_process(
                process,
                network_connections,
                network_counters,
                gpu_data,
            )

            if process_info is not None:
                processes.append(
                    process_info
                )

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            continue

        except Exception:
            continue

    processes.sort(
        key=lambda item: (
            item.get(
                "memory_percent"
            )
            or 0
        ),
        reverse=True,
    )

    return {
        "component": "Processes",
        "available": True,
        "platform": platform.system(),
        "process_count": len(
            processes
        ),
        "processes": processes[
            :limit
        ],
    }