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
    """Print a text file directly to a specific printer using PowerShell Out-Printer.
    
    This bypasses Notepad entirely, avoiding theme-related issues where Notepad
    in dark mode might cause printing problems with label printers.
    """
    try:
        import subprocess
        
        # Read the file content
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Escape single quotes for PowerShell
        ps_content = content.replace("'", "''")
        
        # Use PowerShell Out-Printer - sends raw text directly to printer
        ps_command = f"'{ps_content}' | Out-Printer -Name '{printer_name}'"
        
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_command],
            capture_output=True,
            timeout=30
        )
        return result.returncode == 0
        
    except Exception as e:
        print(f"Direct print failed: {e}")
        return False


def _set_notepad_light_theme() -> None:
    """Force Notepad to use dark theme for printing.
    
    Notepad inherits theme from parent process. This sets the registry 
    to force dark theme for Notepad to ensure consistent printing behavior.
    """
    try:
        import winreg
        key_path = r"Software\Microsoft\Notepad"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        except FileNotFoundError:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
        
        # Theme = 0 means "Use system setting", 1 = Light, 2 = Dark
        winreg.SetValueEx(key, "Theme", 0, winreg.REG_DWORD, 2)
        winreg.CloseKey(key)
    except Exception:
        pass  # If registry access fails, continue anyway


def _print_with_win32_gdi(text: str, printer_name: str) -> bool:
    """Print text using GDI (like Notepad does internally).
    
    This renders text properly with fonts, bypassing Notepad entirely.
    Works reliably from both VS Code and PyInstaller exe.
    Optimized for Brother PT-P700 with 0.94" x 1.50" labels.
    """
    try:
        import win32print
        import win32ui
        
        # Create a device context for the printer
        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(printer_name)
        
        # Get printable area
        height = hdc.GetDeviceCaps(10)  # VERTRES
        
        # Start the document
        hdc.StartDoc("QC Label")
        hdc.StartPage()
        
        # Calculate font size based on label height
        font_height = max(26, height // 8)  # Adaptive font size
        
        # Set up font
        font = win32ui.CreateFont({
            "name": "Arial",
            "height": font_height,
            "weight": 700,  # Bold
        })
        hdc.SelectObject(font)
        
        # Print each line
        lines = [line for line in text.split('\n') if line.strip()]
        line_height = font_height + 4
        start_y = 10
        x = 10  # Left margin
        
        for i, line in enumerate(lines):
            y = start_y + (i * line_height)
            hdc.TextOut(x, y, line)
        
        hdc.EndPage()
        hdc.EndDoc()
        hdc.DeleteDC()
        
        return True
        
    except ImportError:
        return False
    except Exception:
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

    # Debug log file to diagnose PyInstaller print issues
    import sys
    debug_log = os.path.join(os.path.dirname(path), "print_debug.log")
    try:
        with open(debug_log, "a", encoding="utf-8") as dbg:
            dbg.write(f"\n{'='*50}\n")
            dbg.write(f"Timestamp: {now}\n")
            dbg.write(f"sys.frozen: {getattr(sys, 'frozen', False)}\n")
            dbg.write(f"sys.executable: {sys.executable}\n")
            dbg.write(f"os.getcwd(): {os.getcwd()}\n")
            dbg.write(f"File path: {path}\n")
            dbg.write(f"Printer: {printer}\n")
            dbg.write(f"Text to print ({len(text)} chars):\n{text}\n")
    except Exception as e:
        pass

    # ensure parent
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        try:
            os.makedirs(parent, exist_ok=True)
        except Exception:
            pass

    # Write with explicit flush to ensure content is on disk
    with open(path, "w", encoding=encoding) as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())  # Force write to disk

    # Verify file was written correctly
    try:
        with open(debug_log, "a", encoding="utf-8") as dbg:
            if os.path.exists(path):
                file_size = os.path.getsize(path)
                with open(path, "r", encoding=encoding) as verify:
                    content = verify.read()
                dbg.write(f"File exists: True, size: {file_size} bytes\n")
                dbg.write(f"File content verification ({len(content)} chars):\n{content}\n")
            else:
                dbg.write(f"File exists: False - FILE NOT CREATED!\n")
    except Exception as e:
        pass

    def _worker(p: str, d: float, printer: Optional[str], text_to_print: str) -> None:
        debug_log = os.path.join(os.path.dirname(p), "print_debug.log")
        try:
            time.sleep(d)
            if os.name != "nt":
                return

            # Use win32 GDI printing - works from both VS Code and PyInstaller exe
            try:
                with open(debug_log, "a", encoding="utf-8") as dbg:
                    dbg.write(f"_worker: Using win32 GDI print method\n")
                    dbg.write(f"_worker: Printer: {printer}\n")
            except:
                pass

            success = _print_with_win32_gdi(text_to_print, printer)
            
            try:
                with open(debug_log, "a", encoding="utf-8") as dbg:
                    dbg.write(f"_worker: win32 GDI print result: {success}\n")
            except:
                pass

            # OLD METHOD (commented out) - os.startfile with Notepad
            # This doesn't work reliably from PyInstaller exe due to theme issues
            # 
            # # Force Notepad to light theme before printing to avoid
            # # white-on-dark text issues with label printers
            # _set_notepad_light_theme()
            #
            # # Log before calling os.startfile
            # try:
            #     with open(debug_log, "a", encoding="utf-8") as dbg:
            #         dbg.write(f"_worker: About to call os.startfile({p!r}, 'print')\n")
            #         dbg.write(f"_worker: File exists before print: {os.path.exists(p)}\n")
            #         if os.path.exists(p):
            #             dbg.write(f"_worker: File size: {os.path.getsize(p)}\n")
            # except:
            #     pass
            #
            # # Use os.startfile with the system default printer
            # try:
            #     os.startfile(p, "print")
            #     with open(debug_log, "a", encoding="utf-8") as dbg:
            #         dbg.write(f"_worker: os.startfile completed successfully\n")
            # except Exception as e:
            #     with open(debug_log, "a", encoding="utf-8") as dbg:
            #         dbg.write(f"_worker: os.startfile FAILED: {e}\n")

        except Exception as e:
            try:
                with open(debug_log, "a", encoding="utf-8") as dbg:
                    dbg.write(f"_worker: Exception: {e}\n")
            except:
                pass

    t = threading.Thread(target=_worker, args=(path, delay_s, printer, text))
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
