import subprocess
import sys
from pathlib import Path


def build_element_tester():
    """
    Builds the Element Tester application using PyInstaller with predefined arguments.
    """
    project_root = Path(__file__).resolve().parent
    script_path = project_root / "src" / "element_tester" / "system" / "core" / "test_runner.py"
    if not script_path.exists():
        print(f"Error: {script_path} does not exist.")
        sys.exit(1)

    pyinstaller_args = [
        "pyinstaller",
        "--clean",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "ElementTester",
        str(script_path)
    ]

    print("Running PyInstaller with arguments:")
    print(" ".join(pyinstaller_args))

    try:
        subprocess.run(pyinstaller_args, check=True)
        print("Build completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error: {e}")
        sys.exit(e.returncode)


if __name__ == "__main__":
    build_element_tester()
