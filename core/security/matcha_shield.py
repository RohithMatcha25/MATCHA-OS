"""
MATCHA Shield — Priority 3
Real-time antivirus protection using ClamAV + watchdog.
Monitors filesystem, scans on-connect devices, quarantines threats.
"""

import os
import shutil
import hashlib
import json
import datetime
import threading
from pathlib import Path
from typing import Callable, Optional

try:
    import clamd
    CLAMD_AVAILABLE = True
except ImportError:
    CLAMD_AVAILABLE = False

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


QUARANTINE_DIR = Path.home() / ".matcha" / "quarantine"
SHIELD_LOG = Path.home() / ".matcha" / "shield_log.json"


class MatchaShield:
    """
    MATCHA's security module.
    Wraps ClamAV for scanning, watchdog for real-time monitoring.
    Falls back to basic hash-based detection when ClamAV unavailable.
    """

    def __init__(self, alert_callback: Optional[Callable] = None):
        self.alert_callback = alert_callback or self._default_alert
        self.observer = None
        self._scanning = False

        # Ensure quarantine directory exists
        QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
        SHIELD_LOG.parent.mkdir(parents=True, exist_ok=True)

        # ClamAV connection
        self.clam = self._init_clamd()

        print(f"[MATCHA Shield] Initialised. ClamAV: {'available' if self.clam else 'unavailable (fallback mode)'}.")

    def _init_clamd(self):
        """Connect to ClamAV daemon."""
        if not CLAMD_AVAILABLE:
            return None
        try:
            cd = clamd.ClamdUnixSocket()
            cd.ping()
            return cd
        except Exception:
            try:
                cd = clamd.ClamdNetworkSocket()
                cd.ping()
                return cd
            except Exception:
                return None

    def _default_alert(self, threat: dict):
        """Default alert handler — logs to console."""
        print(f"[MATCHA Shield ⚠️ THREAT] {threat['file']} — {threat['threat']}")

    # ─── File Scanning ────────────────────────────────────────────────────────

    def scan_file(self, file_path: str) -> dict:
        """Scan a single file. Returns threat status."""
        file_path = str(file_path)
        if not os.path.exists(file_path):
            return {"file": file_path, "status": "error", "threat": "File not found."}

        # ClamAV scan (preferred)
        if self.clam:
            try:
                result = self.clam.scan(file_path)
                if result:
                    file_key = list(result.keys())[0]
                    status, threat = result[file_key]
                    if status == "FOUND":
                        threat_info = {
                            "file": file_path,
                            "status": "threat",
                            "threat": threat,
                            "timestamp": datetime.datetime.now().isoformat()
                        }
                        self._log_threat(threat_info)
                        self.alert_callback(threat_info)
                        return threat_info
                    else:
                        return {"file": file_path, "status": "clean", "threat": None}
            except Exception as e:
                pass

        # Fallback: basic heuristic scan
        return self._heuristic_scan(file_path)

    def _heuristic_scan(self, file_path: str) -> dict:
        """
        Basic heuristic detection without ClamAV.
        Checks file extension vs content, suspicious patterns.
        """
        SUSPICIOUS_EXTS = {
            ".exe", ".bat", ".cmd", ".vbs", ".ps1", ".msi", ".dll",
            ".scr", ".pif", ".com", ".hta", ".jar", ".jnlp"
        }
        SUSPICIOUS_PATTERNS = [
            b"eval(base64_decode",
            b"exec(base64_decode",
            b"<script>document.cookie",
            b"powershell -encodedcommand",
            b"net user /add",
            b"cmd.exe /c",
        ]

        ext = Path(file_path).suffix.lower()
        result = {"file": file_path, "status": "clean", "threat": None}

        # Check extension
        if ext in SUSPICIOUS_EXTS:
            result["status"] = "suspicious"
            result["threat"] = f"Potentially dangerous file type: {ext}"

        # Check content for suspicious patterns (first 8KB)
        try:
            file_size = os.path.getsize(file_path)
            if file_size < 50 * 1024 * 1024:  # Skip files > 50MB
                with open(file_path, "rb") as f:
                    chunk = f.read(8192)
                chunk_lower = chunk.lower()
                for pattern in SUSPICIOUS_PATTERNS:
                    if pattern in chunk_lower:
                        result["status"] = "suspicious"
                        result["threat"] = f"Suspicious pattern detected: {pattern.decode('utf-8', errors='ignore')}"
                        self._log_threat({**result, "timestamp": datetime.datetime.now().isoformat()})
                        self.alert_callback(result)
                        break
        except (PermissionError, OSError):
            pass

        return result

    def scan_directory(self, directory: str, recursive: bool = True) -> dict:
        """Scan an entire directory."""
        directory = str(directory)
        if not os.path.exists(directory):
            return {"success": False, "error": "Directory not found."}

        self._scanning = True
        threats = []
        scanned = 0
        errors = 0

        try:
            if self.clam:
                # ClamAV has built-in recursive scan
                try:
                    if recursive:
                        results = self.clam.multiscan(directory)
                    else:
                        results = self.clam.scan(directory)

                    for file_path, (status, threat) in (results or {}).items():
                        scanned += 1
                        if status == "FOUND":
                            threat_info = {
                                "file": file_path,
                                "status": "threat",
                                "threat": threat,
                                "timestamp": datetime.datetime.now().isoformat()
                            }
                            threats.append(threat_info)
                            self._log_threat(threat_info)
                            self.alert_callback(threat_info)
                except Exception as e:
                    errors += 1
            else:
                # Walk manually with heuristics
                for root, dirs, files in os.walk(directory):
                    # Skip hidden dirs
                    dirs[:] = [d for d in dirs if not d.startswith(".")]
                    for filename in files:
                        file_path = os.path.join(root, filename)
                        result = self._heuristic_scan(file_path)
                        scanned += 1
                        if result["status"] in ("threat", "suspicious"):
                            threats.append(result)
                    if not recursive:
                        break
        finally:
            self._scanning = False

        summary = (
            f"Scan complete: {scanned} files checked. "
            f"{len(threats)} threat(s) found."
        )

        return {
            "success": True,
            "directory": directory,
            "scanned": scanned,
            "threats": threats,
            "errors": errors,
            "summary": summary
        }

    # ─── Quarantine ───────────────────────────────────────────────────────────

    def quarantine_file(self, file_path: str) -> dict:
        """Move a threat to the quarantine directory."""
        file_path = str(file_path)
        if not os.path.exists(file_path):
            return {"success": False, "error": "File not found."}

        try:
            filename = os.path.basename(file_path)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = QUARANTINE_DIR / f"{timestamp}_{filename}.quar"

            shutil.move(file_path, str(dest))

            self._log_threat({
                "file": file_path,
                "status": "quarantined",
                "quarantine_path": str(dest),
                "timestamp": datetime.datetime.now().isoformat()
            })

            return {
                "success": True,
                "original": file_path,
                "quarantine_path": str(dest),
                "summary": f"Quarantined: {filename}."
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_quarantine(self) -> dict:
        """List quarantined files."""
        try:
            files = list(QUARANTINE_DIR.glob("*.quar"))
            items = [{"path": str(f), "size": f.stat().st_size, "name": f.name} for f in files]
            summary = f"{len(items)} file(s) in quarantine."
            return {"success": True, "files": items, "summary": summary}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def restore_from_quarantine(self, quarantine_path: str, restore_path: str) -> dict:
        """Restore a file from quarantine (user explicitly requests)."""
        try:
            shutil.move(quarantine_path, restore_path)
            return {"success": True, "summary": f"Restored to {restore_path}."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ─── Real-time Monitoring ─────────────────────────────────────────────────

    def start_monitoring(self, watch_paths: list = None) -> dict:
        """Start real-time filesystem monitoring."""
        if not WATCHDOG_AVAILABLE:
            return {"success": False, "error": "watchdog library not available."}

        if self.observer and self.observer.is_alive():
            return {"success": False, "error": "Already monitoring."}

        if watch_paths is None:
            watch_paths = [str(Path.home() / "Downloads"), str(Path.home() / "Desktop")]

        handler = MatchaFileEventHandler(self)
        self.observer = Observer()

        for path in watch_paths:
            if os.path.exists(path):
                self.observer.schedule(handler, path, recursive=True)
                print(f"[MATCHA Shield] Monitoring: {path}")

        self.observer.start()
        return {
            "success": True,
            "watching": watch_paths,
            "summary": f"Real-time monitoring active on {len(watch_paths)} path(s)."
        }

    def stop_monitoring(self) -> dict:
        """Stop real-time monitoring."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
        return {"success": True, "summary": "Monitoring stopped."}

    # ─── Threat Log ───────────────────────────────────────────────────────────

    def _log_threat(self, threat: dict):
        """Log a threat to the shield log file."""
        try:
            log = []
            if SHIELD_LOG.exists():
                with open(SHIELD_LOG, "r") as f:
                    log = json.load(f)
        except Exception:
            log = []

        log.append(threat)
        with open(SHIELD_LOG, "w") as f:
            json.dump(log[-500:], f, indent=2)  # Keep last 500 entries

    def get_threat_log(self, limit: int = 20) -> dict:
        """Return recent threat log entries."""
        try:
            if not SHIELD_LOG.exists():
                return {"success": True, "threats": [], "summary": "No threats logged."}
            with open(SHIELD_LOG, "r") as f:
                log = json.load(f)
            recent = log[-limit:][::-1]
            summary = f"{len(log)} total threats logged. Showing last {len(recent)}."
            return {"success": True, "threats": recent, "summary": summary}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_status(self) -> dict:
        """Shield status report."""
        return {
            "success": True,
            "clamd_available": bool(self.clam),
            "watchdog_available": WATCHDOG_AVAILABLE,
            "monitoring": self.observer is not None and self.observer.is_alive(),
            "quarantine_count": len(list(QUARANTINE_DIR.glob("*.quar"))),
            "summary": (
                f"MATCHA Shield active. "
                f"ClamAV: {'connected' if self.clam else 'offline (heuristic mode)'}. "
                f"Real-time monitoring: {'active' if self.observer and self.observer.is_alive() else 'inactive'}."
            )
        }


class MatchaFileEventHandler(FileSystemEventHandler if WATCHDOG_AVAILABLE else object):
    """Handles real-time file system events."""

    def __init__(self, shield: MatchaShield):
        if WATCHDOG_AVAILABLE:
            super().__init__()
        self.shield = shield

    def on_created(self, event):
        if event.is_directory:
            return
        # Scan newly created files
        result = self.shield.scan_file(event.src_path)
        if result["status"] in ("threat", "suspicious"):
            print(f"[MATCHA Shield] Threat on create: {event.src_path}")

    def on_modified(self, event):
        if event.is_directory:
            return
        # Scan modified files (but not too aggressively)
        ext = Path(event.src_path).suffix.lower()
        suspicious_exts = {".exe", ".bat", ".cmd", ".vbs", ".ps1", ".msi", ".dll", ".sh"}
        if ext in suspicious_exts:
            result = self.shield.scan_file(event.src_path)
            if result["status"] in ("threat", "suspicious"):
                print(f"[MATCHA Shield] Threat on modify: {event.src_path}")


if __name__ == "__main__":
    shield = MatchaShield()
    print(shield.get_status()["summary"])

    # Test heuristic scan on a temp safe file
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"Hello, this is a safe file.")
        tmp_path = f.name

    result = shield.scan_file(tmp_path)
    print(f"Test scan result: {result['status']}")
    os.unlink(tmp_path)
