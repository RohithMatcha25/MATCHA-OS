"""
MATCHA Builder - Actually builds and runs apps.
When user asks to build something, this writes real files and runs them.
"""

import os
import subprocess
import sys
import shutil
import json
import threading
import time
import re
import pathlib
from typing import Optional

WORKSPACE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "workspace")


class MatchaBuilder:
    def __init__(self):
        os.makedirs(WORKSPACE, exist_ok=True)
        self.running_apps = {}  # name -> {process, port, url}
        print(f"[MATCHA Builder] Ready. Workspace: {WORKSPACE}")

    def build_and_run(self, app_name: str, app_type: str, spec: str, brain) -> str:
        """Build a real app, run it, return the URL."""
        app_dir = os.path.join(WORKSPACE, app_name.lower().replace(" ", "-"))
        os.makedirs(app_dir, exist_ok=True)

        try:
            if app_type in ("web", "webapp", "website", "todo", "app"):
                return self._build_flask_app(app_name, app_dir, spec, brain)
            else:
                return self._build_flask_app(app_name, app_dir, spec, brain)
        except Exception as e:
            return f"Build failed: {e}"

    def _build_flask_app(self, app_name: str, app_dir: str, spec: str, brain) -> str:
        """Generate a Flask web app using the brain, write files, start server."""
        port = self._find_free_port()

        # Ask brain to generate the app code
        prompt = (
            f"Build a complete working Flask web app called '{app_name}'.\n"
            f"Spec: {spec}\n\n"
            f"Return ONLY valid Python code for app.py. No explanation. No markdown. Pure Python.\n"
            f"Requirements:\n"
            f"- Use Flask only (no other frameworks)\n"
            f"- Run on port {port}\n"
            f"- Include all routes, HTML templates as strings (use render_template_string), CSS inline\n"
            f"- Make it fully functional and good looking\n"
            f"- At the bottom: if __name__ == '__main__': app.run(port={port}, debug=False)\n"
            f"Return ONLY the Python code, nothing else."
        )

        code = brain.think(prompt)
        code = self._extract_code(code)

        if not code or len(code) < 50:
            return "Could not generate app code. Try again."

        # Write the app file
        app_file = os.path.join(app_dir, "app.py")
        with open(app_file, "w", encoding="utf-8") as f:
            f.write(code)

        # Install flask if needed
        self._ensure_package("flask")

        # Kill old instance if running
        if app_name in self.running_apps:
            try:
                self.running_apps[app_name]["process"].terminate()
            except Exception:
                pass

        # Start the app
        python = sys.executable
        process = subprocess.Popen(
            [python, app_file],
            cwd=app_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        time.sleep(2)  # Let it start

        if process.poll() is not None:
            # Process died — get error
            err = process.stderr.read().decode()[:300]
            # Try to auto-fix
            fix = self._auto_fix(code, err, brain, port)
            if fix:
                with open(app_file, "w", encoding="utf-8") as f:
                    f.write(fix)
                process = subprocess.Popen(
                    [python, app_file],
                    cwd=app_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                time.sleep(2)
                if process.poll() is not None:
                    err2 = process.stderr.read().decode()[:200]
                    return f"Build failed after auto-fix: {err2}"

        url = f"http://localhost:{port}"
        self.running_apps[app_name] = {"process": process, "port": port, "url": url, "dir": app_dir}

        return (
            f"**{app_name} is running.**\n\n"
            f"Open it here: {url}\n\n"
            f"Files saved to: `{app_dir}`"
        )

    def _auto_fix(self, code: str, error: str, brain, port: int) -> Optional[str]:
        """Ask brain to fix broken code."""
        try:
            prompt = (
                f"This Flask app has an error:\n\nERROR:\n{error}\n\nCODE:\n{code}\n\n"
                f"Fix it. Return ONLY the fixed Python code. No explanation. Port must be {port}."
            )
            fixed = brain.think(prompt)
            return self._extract_code(fixed)
        except Exception:
            return None

    def _extract_code(self, text: str) -> str:
        """Strip markdown code fences if brain wraps in them."""
        # Try to extract from ```python ... ```
        match = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        # If it starts with 'from' or 'import' or '#' it's probably raw code
        lines = text.strip().split("\n")
        code_lines = []
        in_code = False
        for line in lines:
            if line.startswith(("from ", "import ", "app ", "def ", "class ", "@", "#", "    ", "\t")):
                in_code = True
            if in_code:
                code_lines.append(line)
        if code_lines:
            return "\n".join(code_lines)
        return text.strip()

    def _find_free_port(self) -> int:
        """Find an available port starting from 8100."""
        import socket
        used = {v["port"] for v in self.running_apps.values()}
        for port in range(8100, 8200):
            if port in used:
                continue
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("", port))
                    return port
            except OSError:
                continue
        return 8100

    def _ensure_package(self, package: str):
        """Install a package if not present."""
        try:
            __import__(package)
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", package, "-q"], check=True)

    def list_apps(self) -> str:
        """List all running apps."""
        if not self.running_apps:
            return "No apps running."
        lines = []
        for name, info in self.running_apps.items():
            alive = "running" if info["process"].poll() is None else "stopped"
            lines.append(f"• **{name}** — {info['url']} ({alive})")
        return "\n".join(lines)

    def stop_app(self, app_name: str) -> str:
        """Stop a running app."""
        if app_name in self.running_apps:
            try:
                self.running_apps[app_name]["process"].terminate()
                del self.running_apps[app_name]
                return f"{app_name} stopped."
            except Exception as e:
                return f"Error stopping {app_name}: {e}"
        return f"No app called '{app_name}' is running."

    def get_app_dir(self, app_name: str) -> str:
        """Return the directory of a built app."""
        key = app_name.lower().replace(" ", "-")
        return os.path.join(WORKSPACE, key)
