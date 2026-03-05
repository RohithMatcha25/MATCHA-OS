@echo off
REM MATCHA OS — Windows Quick Installer (Batch)
REM Run as Administrator

echo.
echo ╔══════════════════════════════════════╗
echo ║      MATCHA OS — Windows Setup      ║
echo ╚══════════════════════════════════════╝
echo.

SET INSTALL_DIR=%USERPROFILE%\.matcha-os

REM Check Python
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo Python not found. Downloading...
    curl -o python-installer.exe https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe
    python-installer.exe /quiet InstallAllUsers=1 PrependPath=1
    del python-installer.exe
)

REM Check Git
git --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo Git not found. Downloading...
    winget install Git.Git -e --silent
)

REM Clone or update MATCHA
IF EXIST "%INSTALL_DIR%" (
    cd /d "%INSTALL_DIR%" && git pull
) ELSE (
    git clone https://github.com/RohithMatcha25/matcha-os "%INSTALL_DIR%"
)

cd /d "%INSTALL_DIR%"

REM Setup virtual environment
python -m venv venv
call venv\Scripts\activate.bat
pip install --quiet -r requirements.txt

REM Create desktop shortcut via PowerShell
powershell -Command "$WShell = New-Object -ComObject WScript.Shell; $Shortcut = $WShell.CreateShortcut('%USERPROFILE%\Desktop\MATCHA OS.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\venv\Scripts\python.exe'; $Shortcut.Arguments = 'main.py'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Save()"

REM Add to startup
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "MATCHA OS" /t REG_SZ /d "\"%INSTALL_DIR%\venv\Scripts\python.exe\" \"%INSTALL_DIR%\main.py\"" /f

echo.
echo ✅ MATCHA OS installed successfully!
echo A shortcut has been added to your Desktop.
echo MATCHA OS will launch automatically on startup.
echo.
pause
