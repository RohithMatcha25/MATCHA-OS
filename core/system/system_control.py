"""
MATCHA System Control — Priority 2
Controls the underlying OS: volume, brightness, apps, files, processes, power.
"""

import subprocess
import os
import sys
import psutil
import shutil
import re
from pathlib import Path
from typing import Optional, List


class SystemControl:
    def __init__(self):
        self.platform = sys.platform
        print(f"[MATCHA System] Initialised on {self.platform}")

    def get_volume(self) -> dict:
        try:
            if self.platform == "linux":
                result = subprocess.run(["pactl","get-sink-volume","@DEFAULT_SINK@"],capture_output=True,text=True,timeout=5)
                if result.returncode == 0:
                    match = re.search(r'(\d+)%', result.stdout)
                    if match:
                        vol = int(match.group(1))
                        return {"success": True, "volume": vol, "summary": f"Volume at {vol}%."}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "Could not get volume."}

    def set_volume(self, level: int) -> dict:
        level = max(0, min(100, level))
        try:
            if self.platform == "linux":
                subprocess.run(["pactl","set-sink-volume","@DEFAULT_SINK@",f"{level}%"],timeout=5)
                return {"success": True, "volume": level, "summary": f"Volume set to {level}%."}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "Platform not supported."}

    def mute(self) -> dict:
        try:
            if self.platform == "linux":
                subprocess.run(["pactl","set-sink-mute","@DEFAULT_SINK@","1"],timeout=5)
                return {"success": True, "summary": "Audio muted."}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "Platform not supported."}

    def unmute(self) -> dict:
        try:
            if self.platform == "linux":
                subprocess.run(["pactl","set-sink-mute","@DEFAULT_SINK@","0"],timeout=5)
                return {"success": True, "summary": "Audio restored."}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "Platform not supported."}

    def get_brightness(self) -> dict:
        try:
            if self.platform == "linux":
                result = subprocess.run(["brightnessctl","g"],capture_output=True,text=True,timeout=5)
                if result.returncode == 0:
                    current = int(result.stdout.strip())
                    result_max = subprocess.run(["brightnessctl","m"],capture_output=True,text=True,timeout=5)
                    max_val = int(result_max.stdout.strip()) if result_max.returncode == 0 else 100
                    pct = int((current/max_val)*100)
                    return {"success": True, "brightness": pct, "summary": f"Brightness at {pct}%."}
        except Exception as e:
            pass
        return {"success": False, "error": "Brightness control unavailable."}

    def set_brightness(self, level: int) -> dict:
        level = max(5, min(100, level))
        try:
            if self.platform == "linux":
                subprocess.run(["brightnessctl","s",f"{level}%"],timeout=5)
                return {"success": True, "brightness": level, "summary": f"Brightness set to {level}%."}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "Platform not supported."}

    def launch_app(self, app_name: str) -> dict:
        app_lower = app_name.lower().strip()

        # Windows app map
        win_app_map = {
            "chrome": ["chrome", "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"],
            "google chrome": ["chrome"],
            "firefox": ["firefox"],
            "edge": ["msedge"],
            "microsoft edge": ["msedge"],
            "brave": ["brave"],
            "notepad": ["notepad"],
            "notepad++": ["notepad++"],
            "calculator": ["calc"],
            "calc": ["calc"],
            "explorer": ["explorer"],
            "file explorer": ["explorer"],
            "task manager": ["taskmgr"],
            "control panel": ["control"],
            "settings": ["ms-settings:"],
            "paint": ["mspaint"],
            "word": ["winword"],
            "excel": ["excel"],
            "powerpoint": ["powerpnt"],
            "outlook": ["outlook"],
            "teams": ["teams"],
            "discord": ["discord"],
            "slack": ["slack"],
            "zoom": ["zoom"],
            "vscode": ["code"],
            "vs code": ["code"],
            "visual studio code": ["code"],
            "vlc": ["vlc"],
            "steam": ["steam"],
            "terminal": ["cmd"],
            "cmd": ["cmd"],
            "powershell": ["powershell"],
            "spotify": ["spotify"],
        }

        # Linux app map
        linux_app_map = {
            "browser": ["google-chrome", "chromium", "firefox"],
            "chrome": ["google-chrome", "chromium"],
            "firefox": ["firefox"],
            "terminal": ["gnome-terminal", "xterm", "konsole"],
            "files": ["nautilus", "thunar", "dolphin"],
            "vscode": ["code"], "vs code": ["code"],
            "calculator": ["gnome-calculator", "kcalc"],
            "spotify": ["spotify"], "vlc": ["vlc"],
        }

        if self.platform == "win32":
            candidates = win_app_map.get(app_lower, [app_lower])
            for cmd in candidates:
                try:
                    if cmd.startswith("ms-"):
                        # Windows Settings URI
                        subprocess.Popen(["start", cmd], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        subprocess.Popen([cmd], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return {"success": True, "app": cmd, "summary": f"Launching {app_name}."}
                except Exception:
                    continue
        else:
            candidates = linux_app_map.get(app_lower, [app_lower])
            for cmd in candidates:
                if shutil.which(cmd):
                    try:
                        subprocess.Popen([cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        return {"success": True, "app": cmd, "summary": f"Launching {app_name}."}
                    except Exception:
                        continue

        return {"success": False, "error": f"'{app_name}' not found. Say 'open {app_name} in browser' if it's a website."}

    def find_files(self, query: str, search_dir: str = None, max_results: int = 10) -> dict:
        if search_dir is None:
            search_dir = str(Path.home())
        try:
            result = subprocess.run(
                ["find", search_dir, "-iname", f"*{query}*", "-not", "-path", "*/.*", "-maxdepth", "6"],
                capture_output=True, text=True, timeout=15
            )
            files = [line for line in result.stdout.strip().split("\n") if line][:max_results]
            if files:
                summary = f"Found {len(files)} file(s) matching '{query}': " + ", ".join([os.path.basename(f) for f in files[:3]])
                return {"success": True, "files": files, "summary": summary}
            else:
                return {"success": False, "error": f"No files found matching '{query}'.", "files": []}
        except Exception as e:
            return {"success": False, "error": str(e), "files": []}

    def list_processes(self, filter_name: str = None) -> dict:
        try:
            procs = []
            for proc in psutil.process_iter(["pid","name","cpu_percent","memory_percent"]):
                try:
                    info = proc.info
                    if filter_name and filter_name.lower() not in info["name"].lower():
                        continue
                    procs.append({"pid": info["pid"], "name": info["name"],
                                  "cpu": round(info["cpu_percent"] or 0, 1),
                                  "memory": round(info["memory_percent"] or 0, 1)})
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            procs.sort(key=lambda x: x["cpu"], reverse=True)
            summary = f"{len(procs)} processes running."
            if procs:
                top = procs[0]
                summary += f" Top CPU: {top['name']} ({top['cpu']}%)."
            return {"success": True, "processes": procs[:20], "summary": summary}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def kill_process(self, identifier) -> dict:
        killed = []
        try:
            if isinstance(identifier, int):
                try:
                    psutil.Process(identifier).kill()
                    killed.append(str(identifier))
                except Exception as e:
                    return {"success": False, "error": str(e)}
            else:
                for proc in psutil.process_iter(["pid","name"]):
                    try:
                        if identifier.lower() in proc.info["name"].lower():
                            proc.kill()
                            killed.append(proc.info["name"])
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            if killed:
                return {"success": True, "killed": killed, "summary": f"Terminated: {', '.join(killed)}."}
            return {"success": False, "error": f"No process matching '{identifier}'."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_system_info(self) -> dict:
        try:
            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            summary = (
                f"CPU: {cpu}%. "
                f"RAM: {ram.percent}% used ({round(ram.used/1e9,1)}GB / {round(ram.total/1e9,1)}GB). "
                f"Disk: {disk.percent}% used ({round(disk.used/1e9,1)}GB / {round(disk.total/1e9,1)}GB)."
            )
            return {"success": True, "cpu_percent": cpu, "ram_percent": ram.percent,
                    "disk_percent": disk.percent, "summary": summary}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def shutdown(self, delay_seconds: int = 0) -> dict:
        try:
            if self.platform == "linux":
                subprocess.Popen(["shutdown","-h","now"])
            return {"success": True, "summary": "Shutdown initiated."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def restart(self) -> dict:
        try:
            if self.platform == "linux":
                subprocess.Popen(["shutdown","-r","now"])
            return {"success": True, "summary": "Restart initiated."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sleep(self) -> dict:
        try:
            if self.platform == "linux":
                subprocess.Popen(["systemctl","suspend"])
            return {"success": True, "summary": "System sleeping."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def lock_screen(self) -> dict:
        try:
            if self.platform == "linux":
                for cmd in [["gnome-screensaver-command","--lock"],["xdg-screensaver","lock"],["loginctl","lock-session"]]:
                    if shutil.which(cmd[0]):
                        subprocess.Popen(cmd)
                        break
            return {"success": True, "summary": "Screen locked."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def handle_command(self, query: str) -> dict:
        query_lower = query.lower()
        if "volume" in query_lower:
            if "mute" in query_lower:
                return self.mute()
            elif "unmute" in query_lower:
                return self.unmute()
            elif "up" in query_lower or "increase" in query_lower:
                current = self.get_volume().get("volume", 50)
                return self.set_volume(current + 10)
            elif "down" in query_lower or "decrease" in query_lower or "lower" in query_lower:
                current = self.get_volume().get("volume", 50)
                return self.set_volume(current - 10)
            else:
                match = re.search(r'(\d+)', query)
                if match:
                    return self.set_volume(int(match.group(1)))
                return self.get_volume()
        elif "brightness" in query_lower:
            match = re.search(r'(\d+)', query)
            if match:
                return self.set_brightness(int(match.group(1)))
            return self.get_brightness()
        elif any(w in query_lower for w in ["open","launch","start"]):
            for prefix in ["open","launch","start"]:
                if prefix in query_lower:
                    app = query_lower.split(prefix,1)[-1].strip()
                    if app:
                        return self.launch_app(app)
        elif any(w in query_lower for w in ["find file","where is"]):
            for prefix in ["find file","find files","where is"]:
                if prefix in query_lower:
                    filename = query_lower.split(prefix,1)[-1].strip()
                    if filename:
                        return self.find_files(filename)
        elif any(w in query_lower for w in ["cpu","ram","memory","disk","system info"]):
            return self.get_system_info()
        elif "sleep" in query_lower:
            return self.sleep()
        elif "lock" in query_lower:
            return self.lock_screen()
        return {"success": False, "error": "System command not recognised."}


if __name__ == "__main__":
    sc = SystemControl()
    print(sc.get_system_info())
    print(sc.list_processes().get("summary"))
