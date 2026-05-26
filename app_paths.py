# app_paths.py
import os
import sys
import platform

def _base_data_dir() -> str:
    system = platform.system()
    if system == "Windows":
        base = os.getenv("APPDATA") or os.path.expanduser("~")
    elif system == "Darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.getenv("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    data = os.path.join(base, "Sistema_CRA")
    os.makedirs(data, exist_ok=True)
    return data

def data_dir() -> str:
    return _base_data_dir()

def path(*parts) -> str:
    return os.path.join(data_dir(), *parts)

def local_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def local_path(*parts) -> str:
    return os.path.join(local_dir(), *parts)
