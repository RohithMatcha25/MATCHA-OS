; MATCHA OS — Windows Installer (NSIS Script)
; Creates a professional Windows installer (.exe)
; Users run this once → MATCHA OS installed, launches on startup

!define APP_NAME "MATCHA OS"
!define APP_VERSION "0.2.0"
!define APP_PUBLISHER "Rohith Matcha"
!define APP_URL "https://github.com/RohithMatcha25/matcha-os"
!define APP_EXE "matcha.exe"
!define INSTALL_DIR "$PROGRAMFILES64\MATCHA OS"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "MATCHA-OS-Setup-${APP_VERSION}.exe"
InstallDir "${INSTALL_DIR}"
InstallDirRegKey HKLM "Software\MATCHA OS" "Install_Dir"
RequestExecutionLevel admin
SetCompressor lzma

;--------------------------------
; Pages
Page license
Page components
Page directory
Page instfiles
UninstPage uninstConfirm
UninstPage instfiles

;--------------------------------
; License
LicenseData "LICENSE.txt"

;--------------------------------
; Sections

Section "MATCHA OS Core" SecCore
  SectionIn RO  ; Required, cannot deselect
  SetOutPath "${INSTALL_DIR}"

  ; Copy all files
  File /r "dist\matcha\*.*"

  ; Create start menu shortcut
  CreateDirectory "$SMPROGRAMS\MATCHA OS"
  CreateShortcut "$SMPROGRAMS\MATCHA OS\MATCHA OS.lnk" "${INSTALL_DIR}\${APP_EXE}"
  CreateShortcut "$DESKTOP\MATCHA OS.lnk" "${INSTALL_DIR}\${APP_EXE}"

  ; Registry entry for uninstall
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MATCHA OS" "DisplayName" "${APP_NAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MATCHA OS" "UninstallString" "${INSTALL_DIR}\uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MATCHA OS" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MATCHA OS" "Publisher" "${APP_PUBLISHER}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MATCHA OS" "URLInfoAbout" "${APP_URL}"

  ; Write uninstaller
  WriteUninstaller "${INSTALL_DIR}\uninstall.exe"
SectionEnd

Section "Launch on Startup" SecStartup
  ; Add to Windows startup
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "MATCHA OS" "${INSTALL_DIR}\${APP_EXE}"
SectionEnd

Section "Desktop Shortcut" SecDesktop
  CreateShortcut "$DESKTOP\MATCHA OS.lnk" "${INSTALL_DIR}\${APP_EXE}"
SectionEnd

;--------------------------------
; Uninstaller

Section "Uninstall"
  ; Remove files
  RMDir /r "${INSTALL_DIR}"

  ; Remove shortcuts
  Delete "$SMPROGRAMS\MATCHA OS\MATCHA OS.lnk"
  RMDir "$SMPROGRAMS\MATCHA OS"
  Delete "$DESKTOP\MATCHA OS.lnk"

  ; Remove registry
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MATCHA OS"
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "MATCHA OS"
  DeleteRegKey HKLM "Software\MATCHA OS"
SectionEnd
