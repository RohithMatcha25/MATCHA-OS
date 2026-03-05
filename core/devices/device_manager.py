"""
MATCHA Device Manager — Priority 5
Detects and manages USB drives, Bluetooth, external devices.
"""

import os
import sys
import json
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, Optional, List

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import pyudev
    UDEV_AVAILABLE = True
except ImportError:
    UDEV_AVAILABLE = False


class DeviceManager:
    """
    Detects and manages external devices.
    USB drives, Bluetooth, external storage.
    """

    def __init__(self, on_device_connected: Optional[Callable] = None,
                 on_device_disconnected: Optional[Callable] = None):
        self.on_connected = on_device_connected or self._default_handler
        self.on_disconnected = on_device_disconnected or self._default_handler
        self._monitor_thread = None
        self._monitoring = False
        self._known_devices = set()

        print(f"[MATCHA Devices] Initialised. udev: {'available' if UDEV_AVAILABLE else 'unavailable'}.")

    def _default_handler(self, device: dict):
        action = device.get("action", "connected")
        print(f"[MATCHA Devices] Device {action}: {device.get('name', 'Unknown')}")

    # ─── USB / External Storage ───────────────────────────────────────────────

    def list_usb_drives(self) -> dict:
        """List connected USB/external drives."""
        drives = []

        try:
            if sys.platform == "linux":
                # Use lsblk for comprehensive disk info
                result = subprocess.run(
                    ["lsblk", "-Jo", "NAME,SIZE,TYPE,MOUNTPOINT,MODEL,VENDOR,TRAN,LABEL"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    for device in data.get("blockdevices", []):
                        # Look for USB transport
                        if device.get("tran") == "usb":
                            drives.append({
                                "name": device.get("model") or device.get("label") or device["name"],
                                "device": f"/dev/{device['name']}",
                                "size": device.get("size", "?"),
                                "type": "USB",
                                "mountpoint": device.get("mountpoint") or "",
                                "children": [
                                    {
                                        "device": f"/dev/{child['name']}",
                                        "mountpoint": child.get("mountpoint") or "",
                                        "size": child.get("size", "?"),
                                        "label": child.get("label", "")
                                    }
                                    for child in device.get("children", [])
                                ]
                            })

            elif sys.platform == "darwin":
                # macOS: diskutil
                result = subprocess.run(
                    ["diskutil", "list", "-plist"],
                    capture_output=True, timeout=10
                )
                # Simplified: just list mounted volumes
                drives = self._get_macos_drives()

            elif sys.platform == "win32":
                drives = self._get_windows_drives()

        except Exception as e:
            pass

        # Also check psutil partitions for mounted drives
        if PSUTIL_AVAILABLE and not drives:
            try:
                for part in psutil.disk_partitions():
                    if "removable" in part.opts.lower() or "usb" in part.device.lower():
                        try:
                            usage = psutil.disk_usage(part.mountpoint)
                            drives.append({
                                "name": part.device,
                                "device": part.device,
                                "size": f"{round(usage.total / 1e9, 1)}GB",
                                "used": f"{round(usage.used / 1e9, 1)}GB",
                                "free": f"{round(usage.free / 1e9, 1)}GB",
                                "mountpoint": part.mountpoint,
                                "type": "External"
                            })
                        except Exception:
                            pass
            except Exception:
                pass

        summary = f"{len(drives)} external drive(s) connected." if drives else "No external drives detected."
        return {"success": True, "drives": drives, "summary": summary}

    def _get_macos_drives(self) -> list:
        """Get drives on macOS."""
        drives = []
        try:
            result = subprocess.run(
                ["df", "-h"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 6 and "/Volumes/" in parts[-1]:
                    drives.append({
                        "name": parts[-1].split("/Volumes/")[-1],
                        "device": parts[0],
                        "size": parts[1],
                        "used": parts[2],
                        "free": parts[3],
                        "mountpoint": parts[-1],
                        "type": "External"
                    })
        except Exception:
            pass
        return drives

    def _get_windows_drives(self) -> list:
        """Get drives on Windows."""
        drives = []
        if PSUTIL_AVAILABLE:
            try:
                for part in psutil.disk_partitions():
                    if "removable" in part.opts.lower():
                        try:
                            usage = psutil.disk_usage(part.mountpoint)
                            drives.append({
                                "name": part.mountpoint,
                                "device": part.device,
                                "size": f"{round(usage.total / 1e9, 1)}GB",
                                "mountpoint": part.mountpoint,
                                "type": "Removable"
                            })
                        except Exception:
                            pass
            except Exception:
                pass
        return drives

    # ─── Bluetooth ────────────────────────────────────────────────────────────

    def list_bluetooth_devices(self) -> dict:
        """List paired/connected Bluetooth devices."""
        devices = []

        try:
            if sys.platform == "linux":
                result = subprocess.run(
                    ["bluetoothctl", "devices"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().split("\n"):
                        if line.startswith("Device"):
                            parts = line.split(" ", 2)
                            if len(parts) >= 3:
                                mac = parts[1]
                                name = parts[2]
                                # Check if connected
                                info = subprocess.run(
                                    ["bluetoothctl", "info", mac],
                                    capture_output=True, text=True, timeout=5
                                )
                                connected = "Connected: yes" in info.stdout
                                devices.append({
                                    "name": name,
                                    "mac": mac,
                                    "connected": connected,
                                    "type": "Bluetooth"
                                })

            elif sys.platform == "darwin":
                # macOS: system_profiler
                result = subprocess.run(
                    ["system_profiler", "SPBluetoothDataType", "-json"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    bt_data = data.get("SPBluetoothDataType", [{}])[0]
                    connected = bt_data.get("device_connected", [])
                    for device in connected:
                        for name, info in device.items():
                            devices.append({
                                "name": name,
                                "mac": info.get("device_address", ""),
                                "connected": True,
                                "type": "Bluetooth"
                            })

        except Exception as e:
            pass

        summary = f"{len(devices)} Bluetooth device(s) found." if devices else "No Bluetooth devices found."
        return {"success": True, "devices": devices, "summary": summary}

    def connect_bluetooth(self, mac: str) -> dict:
        """Connect to a Bluetooth device."""
        try:
            if sys.platform == "linux":
                result = subprocess.run(
                    ["bluetoothctl", "connect", mac],
                    capture_output=True, text=True, timeout=15
                )
                if "Connection successful" in result.stdout:
                    return {"success": True, "summary": f"Connected to {mac}."}
                else:
                    return {"success": False, "error": result.stdout or "Connection failed."}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "Platform not supported."}

    # ─── Auto-mount ───────────────────────────────────────────────────────────

    def mount_drive(self, device: str, mountpoint: str = None) -> dict:
        """Mount an external drive."""
        try:
            if sys.platform == "linux":
                if not mountpoint:
                    # Create a mountpoint
                    dev_name = device.split("/")[-1]
                    mountpoint = f"/media/{os.getenv('USER', 'user')}/{dev_name}"
                    os.makedirs(mountpoint, exist_ok=True)

                result = subprocess.run(
                    ["mount", device, mountpoint],
                    capture_output=True, text=True, timeout=15
                )
                if result.returncode == 0:
                    return {"success": True, "device": device, "mountpoint": mountpoint,
                            "summary": f"Mounted {device} at {mountpoint}."}
                else:
                    return {"success": False, "error": result.stderr}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "Platform not supported."}

    def unmount_drive(self, device: str) -> dict:
        """Safely unmount a drive."""
        try:
            if sys.platform == "linux":
                result = subprocess.run(
                    ["umount", device],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    return {"success": True, "summary": f"Safely removed {device}."}
                else:
                    return {"success": False, "error": result.stderr}
            elif sys.platform == "darwin":
                result = subprocess.run(
                    ["diskutil", "eject", device],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    return {"success": True, "summary": f"Ejected {device}."}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "Platform not supported."}

    # ─── Real-time Device Monitoring ──────────────────────────────────────────

    def start_monitoring(self) -> dict:
        """Start monitoring for device connect/disconnect events."""
        if self._monitoring:
            return {"success": False, "error": "Already monitoring."}

        if UDEV_AVAILABLE and sys.platform == "linux":
            self._start_udev_monitor()
        else:
            # Fallback: polling
            self._start_polling_monitor()

        return {"success": True, "summary": "Device monitoring active."}

    def _start_udev_monitor(self):
        """Use udev for real-time device events (Linux)."""
        def monitor():
            context = pyudev.Context()
            monitor = pyudev.Monitor.from_netlink(context)
            monitor.filter_by(subsystem="block")

            for device in iter(monitor.poll, None):
                if not self._monitoring:
                    break
                action = device.action
                info = {
                    "action": action,
                    "name": device.get("ID_MODEL") or device.sys_name,
                    "device": device.device_node,
                    "vendor": device.get("ID_VENDOR") or "",
                    "type": device.get("ID_BUS") or "Unknown",
                    "size": device.get("ID_PART_ENTRY_SIZE") or ""
                }
                if action == "add":
                    self._known_devices.add(device.sys_name)
                    self.on_connected(info)
                elif action == "remove":
                    self._known_devices.discard(device.sys_name)
                    self.on_disconnected(info)

        self._monitoring = True
        self._monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._monitor_thread.start()

    def _start_polling_monitor(self):
        """Poll for device changes (fallback for non-Linux or when udev unavailable)."""
        def poll():
            initial_drives = self._get_current_drives()

            while self._monitoring:
                time.sleep(3)
                current_drives = self._get_current_drives()

                # New drives
                for drive in current_drives - initial_drives:
                    self.on_connected({"action": "add", "name": drive, "device": drive, "type": "Storage"})

                # Removed drives
                for drive in initial_drives - current_drives:
                    self.on_disconnected({"action": "remove", "name": drive, "device": drive, "type": "Storage"})

                initial_drives = current_drives

        self._monitoring = True
        self._monitor_thread = threading.Thread(target=poll, daemon=True)
        self._monitor_thread.start()

    def _get_current_drives(self) -> set:
        """Get current set of mounted drives."""
        drives = set()
        if PSUTIL_AVAILABLE:
            try:
                for part in psutil.disk_partitions():
                    drives.add(part.device)
            except Exception:
                pass
        return drives

    def stop_monitoring(self) -> dict:
        """Stop device monitoring."""
        self._monitoring = False
        return {"success": True, "summary": "Device monitoring stopped."}

    # ─── Device Info ──────────────────────────────────────────────────────────

    def get_all_devices(self) -> dict:
        """Get comprehensive device overview."""
        usb = self.list_usb_drives()
        bt = self.list_bluetooth_devices()

        summary = f"{usb['summary']} {bt['summary']}"

        return {
            "success": True,
            "usb_drives": usb.get("drives", []),
            "bluetooth": bt.get("devices", []),
            "summary": summary
        }

    def handle_command(self, query: str) -> dict:
        """Route device commands."""
        query_lower = query.lower()

        if any(w in query_lower for w in ["usb", "drive", "external", "storage"]):
            return self.list_usb_drives()
        elif any(w in query_lower for w in ["bluetooth", "bt", "wireless"]):
            return self.list_bluetooth_devices()
        elif any(w in query_lower for w in ["devices", "connected", "plugged"]):
            return self.get_all_devices()
        elif "eject" in query_lower or "unmount" in query_lower or "remove" in query_lower:
            import re
            match = re.search(r'(?:eject|unmount|remove) (/dev/\S+)', query)
            if match:
                return self.unmount_drive(match.group(1))
            return {"success": False, "error": "Specify device path to eject."}

        return self.get_all_devices()


if __name__ == "__main__":
    dm = DeviceManager()
    result = dm.get_all_devices()
    print(result["summary"])

    if result["usb_drives"]:
        for drive in result["usb_drives"]:
            print(f"  USB: {drive['name']} ({drive.get('size', '?')})")

    if result["bluetooth"]:
        for dev in result["bluetooth"]:
            print(f"  BT: {dev['name']} — {'connected' if dev['connected'] else 'paired'}")
