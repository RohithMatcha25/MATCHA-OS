"""
MATCHA OS — Remote updater
Downloads and applies latest files to Windows install
"""
import urllib.request, json, os, sys

BASE = "https://theaters-galleries-firewire-reasoning.trycloudflare.com"

files = [
    "core/brain/__init__.py",
    "core/brain/matcha_brain.py",
    "core/matcha_ai.py",
    "core/online/thinker.py",
    "core/online/web_agent.py",
    "interface/index.html",
    "main.py",
]

install_dir = os.path.dirname(os.path.abspath(__file__))
print(f"Updating MATCHA OS at {install_dir}")

for f in files:
    url = f"{BASE}/source?file={f}"
    dest = os.path.join(install_dir, f.replace("/", os.sep))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        urllib.request.urlretrieve(url, dest)
        print(f"  ✅ {f}")
    except Exception as e:
        print(f"  ❌ {f} — {e}")

print("\nDone! Restart MATCHA OS.")
