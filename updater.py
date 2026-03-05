import urllib.request, os, sys

BASE = "https://theaters-galleries-firewire-reasoning.trycloudflare.com"

FILES = [
    "core/brain/__init__.py",
    "core/brain/matcha_brain.py",
    "core/matcha_ai.py",
    "core/online/thinker.py",
    "core/online/web_agent.py",
    "core/model/weights/matcha_model.json",
    "interface/index.html",
    "main.py",
]

install_dir = os.path.dirname(os.path.abspath(__file__))
print(f"Updating MATCHA OS...")
ok = 0
for f in FILES:
    url = f"{BASE}/source?file={f}"
    dest = os.path.join(install_dir, f.replace("/", os.sep))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        urllib.request.urlretrieve(url, dest)
        print(f"  OK  {f}")
        ok += 1
    except Exception as e:
        print(f"  FAIL {f} — {e}")

print(f"\n{ok}/{len(FILES)} files updated.")
if ok == len(FILES):
    print("All done! Close this window and re-run launch.bat")
else:
    print("Some files failed — check your internet connection")
