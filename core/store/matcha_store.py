"""
MATCHA Store — Install any app by asking
"Hey MATCHA, install Spotify" → downloads and installs
"""

import subprocess
import platform
import requests
import os
import json
from pathlib import Path

PLATFORM = platform.system()

# Curated app catalogue
MATCHA_CATALOGUE = {
    "spotify": {
        "name": "Spotify",
        "description": "Music streaming",
        "linux": "snap install spotify",
        "windows": "winget install Spotify.Spotify",
        "darwin": "brew install --cask spotify"
    },
    "vscode": {
        "name": "Visual Studio Code",
        "description": "Code editor",
        "linux": "snap install code --classic",
        "windows": "winget install Microsoft.VisualStudioCode",
        "darwin": "brew install --cask visual-studio-code"
    },
    "chrome": {
        "name": "Google Chrome",
        "description": "Web browser",
        "linux": "apt install -y google-chrome-stable",
        "windows": "winget install Google.Chrome",
        "darwin": "brew install --cask google-chrome"
    },
    "firefox": {
        "name": "Firefox",
        "description": "Web browser",
        "linux": "apt install -y firefox",
        "windows": "winget install Mozilla.Firefox",
        "darwin": "brew install --cask firefox"
    },
    "discord": {
        "name": "Discord",
        "description": "Voice & chat",
        "linux": "snap install discord",
        "windows": "winget install Discord.Discord",
        "darwin": "brew install --cask discord"
    },
    "vlc": {
        "name": "VLC",
        "description": "Media player",
        "linux": "apt install -y vlc",
        "windows": "winget install VideoLAN.VLC",
        "darwin": "brew install --cask vlc"
    },
    "steam": {
        "name": "Steam",
        "description": "Gaming platform",
        "linux": "apt install -y steam",
        "windows": "winget install Valve.Steam",
        "darwin": "brew install --cask steam"
    },
    "gimp": {
        "name": "GIMP",
        "description": "Image editor",
        "linux": "apt install -y gimp",
        "windows": "winget install GIMP.GIMP",
        "darwin": "brew install --cask gimp"
    },
    "obs": {
        "name": "OBS Studio",
        "description": "Screen recording & streaming",
        "linux": "apt install -y obs-studio",
        "windows": "winget install OBSProject.OBSStudio",
        "darwin": "brew install --cask obs"
    },
    "blender": {
        "name": "Blender",
        "description": "3D creation suite",
        "linux": "snap install blender --classic",
        "windows": "winget install BlenderFoundation.Blender",
        "darwin": "brew install --cask blender"
    },
}


class MatchaStore:
    def __init__(self):
        self.installed = self._load_installed()

    def _load_installed(self):
        path = Path.home() / ".matcha" / "installed_apps.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return []

    def _save_installed(self):
        path = Path.home() / ".matcha" / "installed_apps.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.installed, f)

    def search(self, query: str) -> str:
        query = query.lower().strip()
        matches = []
        for key, app in MATCHA_CATALOGUE.items():
            if query in key or query in app["name"].lower() or query in app["description"].lower():
                matches.append(f"• {app['name']} — {app['description']}")
        if matches:
            return "Found in MATCHA Store:\n" + "\n".join(matches)
        return f"No apps found matching '{query}' in MATCHA Store."

    def install(self, app_name: str) -> str:
        key = app_name.lower().strip()
        # Try fuzzy match
        app = MATCHA_CATALOGUE.get(key)
        if not app:
            for k, v in MATCHA_CATALOGUE.items():
                if key in k or key in v["name"].lower():
                    app = v
                    key = k
                    break

        if not app:
            return f"'{app_name}' not found in MATCHA Store. Try searching first."

        platform_key = PLATFORM.lower()
        if platform_key == "darwin":
            platform_key = "darwin"
        elif platform_key == "windows":
            platform_key = "windows"
        else:
            platform_key = "linux"

        cmd = app.get(platform_key, "")
        if not cmd:
            return f"{app['name']} isn't available for your platform."

        try:
            subprocess.Popen(cmd.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.installed.append(key)
            self._save_installed()
            return f"Installing {app['name']}. This may take a moment."
        except FileNotFoundError:
            return f"{app['name']} install command not found on this system. Run MATCHA OS on your own machine to install apps."
        except Exception as e:
            return f"Install failed: {e}"

    def list_catalogue(self) -> str:
        lines = [f"• {v['name']} — {v['description']}" for v in MATCHA_CATALOGUE.values()]
        return "MATCHA Store — Available apps:\n" + "\n".join(lines)

    def uninstall(self, app_name: str) -> str:
        return f"Uninstall support coming soon. Use your system package manager to remove {app_name}."
