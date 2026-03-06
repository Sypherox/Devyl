import re
import ctypes
import ctypes.wintypes as wt
from datetime import datetime, timedelta

import requests

STRINGS_URL = "https://raw.githubusercontent.com/Sypherox/Devyl/refs/heads/main/scanner/DPS_Strings.txt"

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
MEM_COMMIT = 0x1000
PAGE_NOACCESS = 0x01
PAGE_GUARD = 0x100


def _get_dps_pid() -> str | None:
    try:
        import subprocess
        out = subprocess.check_output(
            'tasklist /svc /FI "Services eq DPS"',
            shell=True, text=True, stderr=subprocess.DEVNULL
        )
        for line in out.splitlines():
            if "DPS" in line:
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1]
    except Exception:
        pass
    return None


def _load_strings() -> dict:
    try:
        resp = requests.get(STRINGS_URL, timeout=10)
        resp.raise_for_status()
    except Exception:
        return {}

    mapping = {}
    for line in resp.text.splitlines():
        line = line.strip()
        if ":::" not in line:
            continue
        name, _, string = line.partition(":::")
        string = string.strip()
        name = name.strip()
        if string:
            mapping[string] = name
    return mapping


def _dump_process_strings(pid: int, min_length: int = 6) -> str:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    handle = kernel32.OpenProcess(
        PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid
    )
    if not handle:
        return ""

    strings_found = []
    address = 0
    mbi = ctypes.create_string_buffer(48)

    try:
        while kernel32.VirtualQueryEx(handle, ctypes.c_void_p(address), mbi, ctypes.sizeof(mbi)):
            region_size = int.from_bytes(mbi.raw[16:24], "little")
            state       = int.from_bytes(mbi.raw[24:28], "little")
            protect     = int.from_bytes(mbi.raw[28:32], "little")

            if (
                state == MEM_COMMIT
                and (protect & PAGE_NOACCESS) == 0
                and (protect & PAGE_GUARD) == 0
                and region_size < 50 * 1024 * 1024
            ):
                buf = ctypes.create_string_buffer(region_size)
                read = ctypes.c_size_t(0)
                if kernel32.ReadProcessMemory(
                    handle, ctypes.c_void_p(address),
                    buf, region_size, ctypes.byref(read)
                ):
                    chunk = buf.raw[: read.value]
                    current = []
                    for byte in chunk:
                        if 32 <= byte < 127:
                            current.append(chr(byte))
                        else:
                            if len(current) >= min_length:
                                strings_found.append("".join(current))
                            current = []
                    if len(current) >= min_length:
                        strings_found.append("".join(current))

            address += region_size
            if address >= 0x7FFFFFFFFFFF:
                break
    finally:
        kernel32.CloseHandle(handle)

    return "\n".join(strings_found)


def _is_suspicious(string: str) -> bool:
    match = re.match(r"^(\d{4})/(\d{2})/(\d{2}):(\d{2}):(\d{2}):(\d{2})$", string)
    if not match:
        return False
    try:
        dt = datetime(
            int(match.group(1)), int(match.group(2)), int(match.group(3)),
            int(match.group(4)), int(match.group(5)), int(match.group(6))
        )
        return dt >= datetime.now() - timedelta(hours=12)
    except ValueError:
        return False


def run_dps_scan() -> list[dict]:
    results = []

    pid = _get_dps_pid()
    if not pid:
        return results

    strings_map = _load_strings()
    if not strings_map:
        return results

    dump_content = _dump_process_strings(int(pid))
    if not dump_content.strip():
        return results

    escaped = {s: re.escape(s) for s in strings_map}
    combined = "|".join(escaped.values())

    found_names = set()

    try:
        pattern = re.compile(combined)
        for match in pattern.finditer(dump_content):
            matched_string = match.group(0)
            name = strings_map.get(matched_string)
            if name and name not in found_names:
                found_names.add(name)
                status = "suspicious" if _is_suspicious(matched_string) else "info"
                results.append({
                    "name": name,
                    "string": matched_string,
                    "status": status
                })
    except re.error:
        for string, name in strings_map.items():
            if string in dump_content and name not in found_names:
                found_names.add(name)
                status = "suspicious" if _is_suspicious(string) else "info"
                results.append({
                    "name": name,
                    "string": string,
                    "status": status
                })

    return results
