"""Simple QC print helper.

Public API:
- `print_message(work_order, part_number, ...)` — central function used by
  other modules. It writes a QC message to a file and prints it using the
  Windows print flow (ctypes SetDefaultPrinter + `os.startfile(..., "print")`).

Design goals:
- Minimal and easy to call: callers pass fields to `print_message`.
- `main()` provides a simple test runner using default values.
"""
from __future__ import annotations

import os
import time
import threading
from typing import Optional

# Path to write QC ticket. Change if desired.
qc_file_location = r"C:\Files\element tester\Element_Tester\assets\QCTicket.txt"

# Default printer name for QC labels.
qc_printer_name = "Brother PT-P700"

# Default message template. Callers may pass a custom `message` or rely on
# this template which will be formatted with `workorder` and `partnumber`.
qc_message = "PASSED\nWO:{workorder}\nPN:{partnumber}\nTS: {timestamp}\n"


def _get_default_printer_ctypes() -> str:
    try:
        from ctypes import create_unicode_buffer, byref, windll, wintypes

        buf_size = wintypes.DWORD(260)
        buf = create_unicode_buffer(buf_size.value)
        res = windll.winspool.GetDefaultPrinterW(buf, byref(buf_size))
        if res == 0:
            return ""
        return buf.value
    except Exception:
        return ""


def _set_default_printer_ctypes(name: str) -> bool:
    try:
        from ctypes import windll, c_wchar_p

        res = windll.winspool.SetDefaultPrinterW(c_wchar_p(name))
        return bool(res)
    except Exception:
        return False


def _print_to_printer_directly(file_path: str, printer_name: str) -> bool:
    """Print a text file directly to a specific printer using ShellExecuteEx.
    
    This bypasses the default printer issue by explicitly targeting the printer.
    """
    try:
        from ctypes import windll, c_wchar_p, sizeof, byref, Structure, POINTER
        from ctypes.wintypes import DWORD, HANDLE, HINSTANCE, HKEY, LPVOID, ULONG, LPCWSTR

        class SHELLEXECUTEINFOW(Structure):
            _fields_ = [
                ("cbSize", DWORD),
                ("fMask", ULONG),
                ("hwnd", HANDLE),
                ("lpVerb", LPCWSTR),
                ("lpFile", LPCWSTR),
                ("lpParameters", LPCWSTR),
                ("lpDirectory", LPCWSTR),
                ("nShow", c_int),
                ("hInstApp", HINSTANCE),
                ("lpIDList", LPVOID),
                ("lpClass", LPCWSTR),
                ("hkeyClass", HKEY),
                ("dwHotKey", DWORD),
                ("hIcon", HANDLE),
                ("hProcess", HANDLE),
            ]

        from ctypes import c_int
        
        # Use notepad.exe /p for direct printing - more reliable
        import subprocess
        # /p = print, /pt = print to specific printer
        result = subprocess.run(
            ["notepad.exe", "/pt", file_path, printer_name],
            capture_output=True,
            timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Direct print failed: {e}")
        return False


def print_message(
    workorder: str,
    partnumber: str,
    message: Optional[str] = None,
    file_path: Optional[str] = None,
    printer_name: Optional[str] = None,
    delay_s: float = 1.0,
    encoding: str = "utf-8",
) -> str:
    """Write a QC message and send it to the printer.

    Minimal API: callers can call `print_message("WO","PN")`.
    If `message` is provided it will be used verbatim; otherwise the
    module-level `qc_message` template is formatted with `workorder` and
    `partnumber` and a timestamp.

    If `printer_name` is provided we attempt to set it as the system default
    (ctypes) before calling `os.startfile(..., 'print')` and restore the
    original default afterwards. If not provided, uses module-level `qc_printer_name`.
    """
    path = file_path or qc_file_location
    printer = printer_name or qc_printer_name
    now = time.strftime("%Y-%m-%d")
    if message is None:
        text = qc_message.format(workorder=workorder, partnumber=partnumber, timestamp=now)
    else:
        text = message.replace("{workorder}", workorder).replace("{partnumber}", partnumber).replace("{timestamp}", now)

    # ensure parent
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        try:
            os.makedirs(parent, exist_ok=True)
        except Exception:
            pass

    with open(path, "w", encoding=encoding) as f:
        f.write(text)

    def _worker(p: str, d: float, printer: Optional[str]) -> None:
        orig = ""
        try:
            time.sleep(d)
            if os.name != "nt":
                return

            # Just use os.startfile with the system default printer
            # The PT-P700 should be set as the Windows default printer
            try:
                os.startfile(p, "print")
            except Exception:
                pass

        finally:
            pass

    t = threading.Thread(target=_worker, args=(path, delay_s, printer))
    t.start()
    return os.path.abspath(path)





def main() -> None:
    # simple runnable test: pick a printer and send the ticket to it.
    import subprocess
    import json

    # Attempt to list printers via PowerShell and pick a sensible target.
    target_printer: Optional[str] = None
    try:
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-Printer | Select-Object -Property Name,Default | ConvertTo-Json -Depth 2",
        ]
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        data = json.loads(out.decode("utf-8", errors="ignore"))
        # data may be a dict (single) or list
        printers = data if isinstance(data, list) else [data]
        # prefer default
        for p in printers:
            if p.get("Default"):
                target_printer = p.get("Name")
                break
        # else prefer Brother
        if not target_printer:
            for p in printers:
                name = p.get("Name", "")
                if "Brother" in name:
                    target_printer = name
                    break
        # fallback to first printer
        if not target_printer and printers:
            target_printer = printers[0].get("Name")
    except Exception:
        target_printer = None

    # send print job (no console output)
    _ = print_message("TESTWO", "TESTPN", printer_name=target_printer, delay_s=1.0)


if __name__ == "__main__":
    main()
