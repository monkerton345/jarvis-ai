"""
System information and control skill for Jarvis.
"""
import logging
import platform
import re
import subprocess

logger = logging.getLogger("jarvis.skills.system")

SYSTEM_KEYWORDS = [
    "cpu", "memory", "ram", "disk", "battery", "system", "computer",
    "specs", "processor", "storage", "performance", "temperature",
    "open", "launch", "start", "run", "close", "shutdown", "restart"
]

APP_MAP = {
    "chrome": {"windows": "chrome.exe", "darwin": "Google Chrome", "linux": "google-chrome"},
    "firefox": {"windows": "firefox.exe", "darwin": "Firefox", "linux": "firefox"},
    "notepad": {"windows": "notepad.exe", "darwin": "TextEdit", "linux": "gedit"},
    "calculator": {"windows": "calc.exe", "darwin": "Calculator", "linux": "gnome-calculator"},
    "terminal": {"windows": "wt.exe", "darwin": "Terminal", "linux": "gnome-terminal"},
    "explorer": {"windows": "explorer.exe", "darwin": "Finder", "linux": "nautilus"},
    "spotify": {"windows": "Spotify.exe", "darwin": "Spotify", "linux": "spotify"},
    "vscode": {"windows": "code.cmd", "darwin": "Visual Studio Code", "linux": "code"},
}


def handle(query: str) -> str | None:
    """Return system context or perform system action if relevant."""
    q = query.lower()
    if not any(kw in q for kw in SYSTEM_KEYWORDS):
        return None

    # App launch
    launch_match = re.search(r"(?:open|launch|start|run) ([a-zA-Z\s]+?)(?:\s|$|\?)", q)
    if launch_match:
        app_name = launch_match.group(1).strip()
        return _launch_app(app_name)

    # System info
    if any(kw in q for kw in ["cpu", "memory", "ram", "disk", "battery", "specs", "system info"]):
        return _get_system_info()

    return None


def _get_system_info() -> str:
    """Gather and return system information."""
    try:
        import psutil

        cpu_percent = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count()
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        mem_used_gb = mem.used / (1024 ** 3)
        mem_total_gb = mem.total / (1024 ** 3)
        disk_used_gb = disk.used / (1024 ** 3)
        disk_total_gb = disk.total / (1024 ** 3)

        info = (
            f"System: {platform.system()} {platform.release()}, "
            f"CPU at {cpu_percent}% ({cpu_count} cores), "
            f"RAM {mem_used_gb:.1f}GB of {mem_total_gb:.1f}GB used ({mem.percent}%), "
            f"Disk {disk_used_gb:.1f}GB of {disk_total_gb:.1f}GB used ({disk.percent}%). "
            f"Report these stats naturally in character."
        )

        # Battery if available
        try:
            battery = psutil.sensors_battery()
            if battery:
                status = "charging" if battery.power_plugged else "on battery"
                info += f" Battery at {battery.percent:.0f}%, {status}."
        except Exception:
            pass

        return info

    except ImportError:
        sys_info = f"System: {platform.system()} {platform.release()}, {platform.processor()}"
        return f"{sys_info}. Note: psutil not installed for detailed stats."
    except Exception as e:
        return f"System info unavailable: {e}"


def _launch_app(app_name: str) -> str:
    """Launch an application."""
    system = platform.system().lower()
    app_key = app_name.lower().replace(" ", "")

    # Find in app map
    for key, platforms in APP_MAP.items():
        if key in app_key or app_key in key:
            executable = platforms.get(system)
            if executable:
                try:
                    if system == "windows":
                        subprocess.Popen(["start", executable], shell=True)
                    elif system == "darwin":
                        subprocess.Popen(["open", "-a", executable])
                    else:
                        subprocess.Popen([executable])
                    return f"Opening {app_name}. Let the user know it's launching."
                except Exception as e:
                    return f"Failed to open {app_name}: {e}. Let the user know."

    # Try opening directly
    try:
        if system == "windows":
            subprocess.Popen(["start", app_name], shell=True)
        elif system == "darwin":
            subprocess.Popen(["open", "-a", app_name])
        else:
            subprocess.Popen([app_name.lower()])
        return f"Attempting to open {app_name}."
    except Exception as e:
        return f"Could not find or open '{app_name}'. Inform the user it may not be installed."
