import json
import platform
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
    ):
        return default


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


def _empty_network():
    return {
        "available": False,
        "bytes_sent": None,
        "bytes_received": None,
        "bytes_sent_per_sec": None,
        "bytes_received_per_sec": None,
        "byte_counters_available": False,
        "connection_count": 0,
        "connections": [],
        "source": None,
    }


def _collect_network_connections():
    grouped = {}

    if platform.system() != "Windows":
        return grouped

    try:
        script = (
            "$ErrorActionPreference='SilentlyContinue'; "
            "Get-NetTCPConnection | "
            "Select-Object OwningProcess,LocalAddress,LocalPort,"
            "RemoteAddress,RemotePort,State | "
            "ConvertTo-Json -Compress"
        )

        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                script,
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode != 0:
            return grouped

        output = result.stdout.strip()

        if not output:
            return grouped

        data = json.loads(output)

        if isinstance(data, dict):
            data = [data]

        for item in data:
            try:
                pid = int(
                    item.get(
                        "OwningProcess"
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            connection = {
                "local_address": item.get(
                    "LocalAddress"
                ),
                "local_port": item.get(
                    "LocalPort"
                ),
                "remote_address": item.get(
                    "RemoteAddress"
                ),
                "remote_port": item.get(
                    "RemotePort"
                ),
                "state": item.get(
                    "State"
                ),
            }

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
                    "source": (
                        "Windows TCP connections"
                    ),
                }

            grouped[pid][
                "connections"
            ].append(connection)

            grouped[pid][
                "connection_count"
            ] += 1

    except (
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ):
        return {}

    except Exception:
        return {}

    return grouped


def _collect_network_counters():
    """
    Attempt to collect Windows per-process network
    byte counters.

    Windows exposes network counters through several
    performance-counter providers. Availability varies
    between Windows versions and processes.

    Returns:
        {
            pid: {
                bytes_sent,
                bytes_received,
                bytes_sent_per_sec,
                bytes_received_per_sec,
                byte_counters_available,
                source
            }
        }
    """

    grouped = {}

    if platform.system() != "Windows":
        return grouped

    try:
        script = r"""
$ErrorActionPreference = 'SilentlyContinue'

$counters = @(
    '\Process(*)\IO Read Bytes/sec',
    '\Process(*)\IO Write Bytes/sec'
)

$result = Get-Counter -Counter $counters -ErrorAction SilentlyContinue

if ($null -eq $result) {
    exit 1
}

$result.CounterSamples |
    Select-Object InstanceName,Path,CookedValue |
    ConvertTo-Json -Compress
"""

        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                script,
            ],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )

        if result.returncode != 0:
            return grouped

        output = result.stdout.strip()

        if not output:
            return grouped

        data = json.loads(output)

        if isinstance(data, dict):
            data = [data]

        for item in data:
            instance_name = str(
                item.get(
                    "InstanceName",
                    "",
                )
            )

            if not instance_name:
                continue

            pid_marker = (
                instance_name
                .lower()
                .split("#")[0]
            )

            # Performance-counter process instances
            # use names such as:
            #
            # chrome
            # chrome#1
            #
            # The process ID itself isn't directly
            # encoded in these counters, so we only
            # use the counters when Windows exposes
            # an unambiguous process instance.
            #
            # We therefore do not assign ambiguous
            # counters to PIDs.

            path = str(
                item.get(
                    "Path",
                    "",
                )
            )

            cooked_value = item.get(
                "CookedValue"
            )

            try:
                value = float(
                    cooked_value
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            lower_path = path.lower()

            if "io read bytes/sec" in lower_path:
                counter_type = "read"

            elif "io write bytes/sec" in lower_path:
                counter_type = "write"

            else:
                continue

            key = (
                pid_marker,
                counter_type,
            )

            if key not in grouped:
                grouped[key] = {
                    "instance_name": (
                        instance_name
                    ),
                    "read_per_sec": None,
                    "write_per_sec": None,
                }

            if counter_type == "read":
                grouped[key][
                    "read_per_sec"
                ] = max(
                    0.0,
                    value,
                )

            else:
                grouped[key][
                    "write_per_sec"
                ] = max(
                    0.0,
                    value,
                )

    except (
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ):
        return {}

    except Exception:
        return {}

    return grouped


def _collect_gpu_data():
    grouped = {}

    if platform.system() != "Windows":
        return grouped

    try:
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

        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                script,
            ],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )

        if result.returncode != 0:
            return grouped

        output = result.stdout.strip()

        if not output:
            return grouped

        data = json.loads(output)

        if isinstance(data, dict):
            data = [data]

        for item in data:
            instance_name = str(
                item.get(
                    "InstanceName",
                    "",
                )
            )

            if not instance_name:
                continue

            lower_name = (
                instance_name.lower()
            )

            marker = "pid_"

            marker_index = (
                lower_name.find(
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

            for character in lower_name[
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
                    "".join(pid_chars)
                )

                usage = float(
                    item.get(
                        "CookedValue",
                        0,
                    )
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
            ] += max(
                0.0,
                usage,
            )

            grouped[pid][
                "engine_count"
            ] += 1

    except (
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ):
        return {}

    except Exception:
        return {}

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

    return {
        "memory_percent": round(
            float(
                memory_percent or 0
            ),
            2,
        ),
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
            0,
            time.time()
            - float(create_time),
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
        path_string = str(path)

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

    real_path = (
        executable
        if _is_real_executable_path(
            executable
        )
        else None
    )

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
):
    connection = connection_data.get(
        pid
    )

    if connection is None:
        return {
            "available": True,
            "bytes_sent": None,
            "bytes_received": None,
            "bytes_sent_per_sec": None,
            "bytes_received_per_sec": None,
            "byte_counters_available": False,
            "connection_count": 0,
            "connections": [],
            "source": (
                "Windows TCP connections"
            ),
        }

    return {
        "available": connection.get(
            "available",
            True,
        ),
        "bytes_sent": connection.get(
            "bytes_sent"
        ),
        "bytes_received": connection.get(
            "bytes_received"
        ),
        "bytes_sent_per_sec": connection.get(
            "bytes_sent_per_sec"
        ),
        "bytes_received_per_sec": connection.get(
            "bytes_received_per_sec"
        ),
        "byte_counters_available": connection.get(
            "byte_counters_available",
            False,
        ),
        "connection_count": connection.get(
            "connection_count",
            0,
        ),
        "connections": connection.get(
            "connections",
            [],
        ),
        "source": connection.get(
            "source",
            "Windows TCP connections",
        ),
    }


def _build_gpu(pid, gpu_data):
    return gpu_data.get(
        pid,
        {
            "available": True,
            "usage_percent": 0.0,
            "engine_count": 0,
            "source": (
                "Windows GPU Engine"
            ),
        },
    )


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
    )

    # Network performance counters use
    # process-instance names rather than
    # directly exposing PIDs. Therefore only
    # unambiguous counters should be attached
    # to a process.
    #
    # We deliberately do not guess here.
    counter_candidates = [
        data
        for key, data
        in network_counters.items()
        if data.get(
            "pid"
        ) == pid
    ]

    if len(counter_candidates) == 1:
        counter = counter_candidates[0]

        network[
            "bytes_sent_per_sec"
        ] = counter.get(
            "bytes_sent_per_sec"
        )

        network[
            "bytes_received_per_sec"
        ] = counter.get(
            "bytes_received_per_sec"
        )

        network[
            "byte_counters_available"
        ] = True

        network[
            "source"
        ] = (
            "Windows process "
            "network performance counters"
        )

    gpu = _build_gpu(
        pid,
        gpu_data,
    )

    return {
        "pid": pid,
        "name": name or "Unknown",

        "cpu_percent": cpu_percent,

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
        limit = int(limit)
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

    for process in process_list:
        try:
            process.cpu_percent(
                interval=None
            )
        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            continue

    time.sleep(0.1)

    network_connections = (
        _collect_network_connections()
    )

    network_counters = (
        _collect_network_counters()
    )

    gpu_data = (
        _collect_gpu_data()
    )

    processes = []

    for process in process_list:
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