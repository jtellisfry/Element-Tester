"""Test QC print helper using win32print directly.

This bypasses Notepad entirely and sends raw text straight to the printer.
This should work from both VS Code and PyInstaller exe.

Usage:
    python -m element_tester.system.procedures.print_qctest
    
Or from project root:
    python src/element_tester/system/procedures/print_qctest.py
"""
from __future__ import annotations

import os
import sys
import time

# Default printer name for QC labels
PRINTER_NAME = "Brother PT-P700"

# Test message
TEST_MESSAGE = "PASSED\nWO:WIN32TEST\nPN:WIN32PN\nTS: {timestamp}\n"


def print_with_win32(text: str, printer_name: str) -> bool:
    """Print text directly to printer using win32print.
    
    This bypasses Notepad and all GUI, sending raw text to the printer.
    """
    try:
        import win32print
        import win32ui
        from win32con import DC_PAPERS
        
        # Open the printer
        hprinter = win32print.OpenPrinter(printer_name)
        try:
            # Start a print job
            job_info = ("QC Label", None, "RAW")
            win32print.StartDocPrinter(hprinter, 1, job_info)
            try:
                win32print.StartPagePrinter(hprinter)
                # Write the text as bytes
                win32print.WritePrinter(hprinter, text.encode('utf-8'))
                win32print.EndPagePrinter(hprinter)
            finally:
                win32print.EndDocPrinter(hprinter)
        finally:
            win32print.ClosePrinter(hprinter)
        
        print(f"[win32print] Successfully sent to '{printer_name}'")
        return True
        
    except ImportError as e:
        print(f"[win32print] Import error: {e}")
        print("  Install with: pip install pywin32")
        return False
    except Exception as e:
        print(f"[win32print] Error: {e}")
        return False


def print_with_win32_gdi(text: str, printer_name: str) -> bool:
    """Print text using GDI (like Notepad does internally).
    
    This renders text properly with fonts, not raw bytes.
    Optimized for Brother PT-P700 with 0.94" x 1.50" labels.
    """
    try:
        import win32print
        import win32ui
        import win32con
        
        # Create a device context for the printer
        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(printer_name)
        
        # Get printer resolution
        dpi_x = hdc.GetDeviceCaps(88)  # LOGPIXELSX
        dpi_y = hdc.GetDeviceCaps(90)  # LOGPIXELSY
        print(f"  Printer DPI: {dpi_x} x {dpi_y}")
        
        # Get printable area
        width = hdc.GetDeviceCaps(8)   # HORZRES
        height = hdc.GetDeviceCaps(10) # VERTRES
        print(f"  Printable area: {width} x {height} pixels")
        
        # Start the document
        hdc.StartDoc("QC Label")
        hdc.StartPage()
        
        # Calculate font size based on label height
        # For a small label, use smaller font
        font_height = max(26, height // 8)  # Adaptive font size
        
        # Set up font - use a simple font
        font = win32ui.CreateFont({
            "name": "Arial",
            "height": font_height,
            "weight": 700,  # Bold
        })
        hdc.SelectObject(font)
        
        # Print each line, centered or left-aligned
        lines = [line for line in text.split('\n') if line.strip()]
        total_lines = len(lines)
        line_height = font_height + 4
        
        # Start from top with small margin
        start_y = 10
        x = 10  # Left margin
        
        for i, line in enumerate(lines):
            y = start_y + (i * line_height)
            hdc.TextOut(x, y, line)
        
        hdc.EndPage()
        hdc.EndDoc()
        hdc.DeleteDC()
        
        print(f"[win32 GDI] Successfully sent to '{printer_name}'")
        return True
        
    except ImportError as e:
        print(f"[win32 GDI] Import error: {e}")
        return False
    except Exception as e:
        print(f"[win32 GDI] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_with_subprocess_notepad(file_path: str, printer_name: str) -> bool:
    """Print using notepad.exe /pt (print to specific printer)."""
    try:
        import subprocess
        
        result = subprocess.run(
            ["notepad.exe", "/pt", file_path, printer_name],
            capture_output=True,
            timeout=30
        )
        print(f"[notepad /pt] Return code: {result.returncode}")
        if result.stderr:
            print(f"[notepad /pt] stderr: {result.stderr.decode()}")
        return result.returncode == 0
        
    except Exception as e:
        print(f"[notepad /pt] Error: {e}")
        return False


def print_with_powershell(text: str, printer_name: str) -> bool:
    """Print using PowerShell Out-Printer."""
    try:
        import subprocess
        
        # Escape for PowerShell
        ps_text = text.replace("'", "''")
        ps_cmd = f"'{ps_text}' | Out-Printer -Name '{printer_name}'"
        
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            timeout=30
        )
        print(f"[PowerShell] Return code: {result.returncode}")
        if result.stderr:
            print(f"[PowerShell] stderr: {result.stderr.decode()}")
        return result.returncode == 0
        
    except Exception as e:
        print(f"[PowerShell] Error: {e}")
        return False


def main():
    print("=" * 60)
    print("QC Print Test - Bypassing Notepad")
    print("=" * 60)
    print(f"sys.frozen: {getattr(sys, 'frozen', False)}")
    print(f"sys.executable: {sys.executable}")
    print(f"Printer: {PRINTER_NAME}")
    print()
    
    timestamp = time.strftime("%Y-%m-%d")
    text = TEST_MESSAGE.format(timestamp=timestamp)
    
    print(f"Text to print:\n{text}")
    print("-" * 40)
    
    # Write to temp file for methods that need a file
    temp_file = os.path.join(os.environ.get('TEMP', '.'), 'qc_test_print.txt')
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"Temp file: {temp_file}")
    print()
    
    # Test only Method 2 (GDI) with QCTicket.txt format
    print("Testing Method 2: win32 GDI with QCTicket format...")
    text2 = f"PASSED\nWO:VSCODE_TEST\nPN:VSCODE_PN\nTS: {timestamp}\n"
    result2 = print_with_win32_gdi(text2, PRINTER_NAME)
    print()
    
    # Skip other methods for now
    # print("Testing Method 1: win32print RAW...")
    # text1 = f"=M1=RAW="
    # result1 = print_with_win32(text1, PRINTER_NAME)
    # print("Press Enter after checking if M1 printed...")
    # input()
    
    # print("Testing Method 3: notepad /pt...")
    # text3 = f"=M3=NPT="
    # with open(temp_file, 'w', encoding='utf-8') as f:
    #     f.write(text3)
    # result3 = print_with_subprocess_notepad(temp_file, PRINTER_NAME)
    # print("Press Enter after checking if M3 printed...")
    # input()
    
    # print("Testing Method 4: PowerShell Out-Printer...")
    # text4 = f"=M4=PSH="
    # result4 = print_with_powershell(text4, PRINTER_NAME)
    # print("Press Enter after checking if M4 printed...")
    # input()
    
    print("=" * 60)
    print("Done! Check if the label printed correctly.")


if __name__ == "__main__":
    main()
