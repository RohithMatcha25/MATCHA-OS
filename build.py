"""
MATCHA OS — Package Builder
Creates distributable packages for Windows, Linux, macOS.
Run: python build.py [windows|linux|macos|all]
"""

import os
import sys
import shutil
import subprocess
import platform
import zipfile
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
VERSION = "0.3.0"

EXCLUDE = {
    "__pycache__", "*.pyc", "*.pyo", ".git",
    "venv", "*.egg-info", "dist", "build",
    "core/memory/*.db", "*.log"
}


def clean():
    """Clean previous build artifacts."""
    for d in [DIST_DIR, BUILD_DIR]:
        if d.exists():
            shutil.rmtree(d)
    DIST_DIR.mkdir(parents=True)
    BUILD_DIR.mkdir(parents=True)
    print("✅ Clean.")


def copy_source():
    """Copy source files to build directory."""
    src = BUILD_DIR / "matcha-os"
    src.mkdir(parents=True)

    for item in ROOT.iterdir():
        if item.name in {"dist", "build", "venv", ".git", "__pycache__"}:
            continue
        if item.is_dir():
            shutil.copytree(item, src / item.name,
                          ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.db"))
        else:
            shutil.copy2(item, src / item.name)

    print(f"✅ Source copied to {src}")
    return src


def build_linux(src: Path):
    """Create Linux tarball + install script."""
    print("\n📦 Building Linux package...")

    # Create tarball
    tarball = DIST_DIR / f"matcha-os-{VERSION}-linux.tar.gz"
    import tarfile
    with tarfile.open(str(tarball), "w:gz") as tar:
        tar.add(str(src), arcname="matcha-os")

    # Make install script executable
    install_script = DIST_DIR / "install-linux.sh"
    shutil.copy(ROOT / "installer" / "linux" / "install.sh", install_script)
    os.chmod(install_script, 0o755)

    print(f"✅ Linux: {tarball.name} ({tarball.stat().st_size // 1024}KB)")
    return tarball


def build_macos(src: Path):
    """Create macOS zip + installer."""
    print("\n📦 Building macOS package...")

    zip_path = DIST_DIR / f"matcha-os-{VERSION}-macos.zip"
    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
        for file in src.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(src.parent))

    install_script = DIST_DIR / "install-macos.sh"
    shutil.copy(ROOT / "installer" / "macos" / "install.sh", install_script)
    os.chmod(install_script, 0o755)

    print(f"✅ macOS: {zip_path.name} ({zip_path.stat().st_size // 1024}KB)")
    return zip_path


def build_windows(src: Path):
    """Create Windows zip + install batch file."""
    print("\n📦 Building Windows package...")

    zip_path = DIST_DIR / f"matcha-os-{VERSION}-windows.zip"
    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
        for file in src.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(src.parent))

    install_bat = DIST_DIR / "install-windows.bat"
    shutil.copy(ROOT / "installer" / "windows" / "install.bat", install_bat)

    print(f"✅ Windows: {zip_path.name} ({zip_path.stat().st_size // 1024}KB)")
    return zip_path


def build_readme():
    """Create installation README."""
    content = f"""# MATCHA OS v{VERSION}
> Your AI. Your machine. Just ask.

## Installation

### Windows
1. Download `matcha-os-{VERSION}-windows.zip`
2. Extract to a folder
3. Run `install-windows.bat` as Administrator
4. MATCHA OS will appear on your Desktop

### Linux
1. Download `matcha-os-{VERSION}-linux.tar.gz` and `install-linux.sh`
2. Run: `chmod +x install-linux.sh && ./install-linux.sh`
3. Launch: `matcha` or find it in your app launcher

### macOS
1. Download `matcha-os-{VERSION}-macos.zip` and `install-macos.sh`
2. Run: `chmod +x install-macos.sh && ./install-macos.sh`
3. Double-click "MATCHA OS" on your Desktop

## Requirements
- Python 3.10+ (installer handles this automatically)
- 4GB RAM minimum (8GB recommended)
- 2GB free disk space
- Internet connection for online features (optional)

## First Launch
Open your browser and go to: http://localhost:8080

Say or type anything to MATCHA.
Say "Hey MATCHA" to activate voice mode.

## Built by
Rohith Matcha
"""
    readme = DIST_DIR / "README.md"
    readme.write_text(content)
    print(f"✅ README created.")


def build_all():
    print(f"\n{'='*50}")
    print(f"  MATCHA OS v{VERSION} — Build System")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")

    clean()
    src = copy_source()
    build_linux(src)
    build_macos(src)
    build_windows(src)
    build_readme()

    print(f"\n{'='*50}")
    print(f"  ✅ Build complete!")
    print(f"  Output: {DIST_DIR}/")
    files = list(DIST_DIR.iterdir())
    total = sum(f.stat().st_size for f in files if f.is_file()) // 1024
    print(f"  Files: {len(files)} | Total size: {total}KB")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "all"

    clean()
    src = copy_source()

    if target in ("all", "linux"):
        build_linux(src)
    if target in ("all", "macos"):
        build_macos(src)
    if target in ("all", "windows"):
        build_windows(src)

    build_readme()
    print("\n✅ Done.")
