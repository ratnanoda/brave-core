Unicode true
RequestExecutionLevel user
SetCompressor /SOLID lzma

!include "MUI2.nsh"
!include "FileFunc.nsh"

!ifndef PAYLOAD_DIR
  !error "PAYLOAD_DIR must point to the staged Haly payload"
!endif
!ifndef OUTPUT_FILE
  !define OUTPUT_FILE "HalySetup-x64.exe"
!endif
!ifndef HALY_VERSION
  !define HALY_VERSION "1.92.144.1"
!endif
!ifndef HALY_DISPLAY_VERSION
  !define HALY_DISPLAY_VERSION "1.92.144-haly.1"
!endif
!ifndef HALY_ICON
  !error "HALY_ICON must point to Haly.ico"
!endif

!define PRODUCT_NAME "Haly"
!define PRODUCT_PUBLISHER "Haly Authors"
!define PRODUCT_REG_KEY "Software\Haly"
!define PRODUCT_UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\HalyBrowser"

Name "${PRODUCT_NAME}"
OutFile "${OUTPUT_FILE}"
InstallDir "$LOCALAPPDATA\Programs\Haly"
InstallDirRegKey HKCU "${PRODUCT_REG_KEY}" "InstallDir"
Icon "${HALY_ICON}"
UninstallIcon "${HALY_ICON}"
BrandingText "Haly Browser"
ShowInstDetails show
ShowUninstDetails show

VIProductVersion "${HALY_VERSION}"
VIAddVersionKey /LANG=1033 "ProductName" "Haly Browser"
VIAddVersionKey /LANG=1033 "FileDescription" "Haly Browser Installer"
VIAddVersionKey /LANG=1033 "CompanyName" "Haly Authors"
VIAddVersionKey /LANG=1033 "LegalCopyright" "Copyright (c) 2026 The Haly Authors"
VIAddVersionKey /LANG=1033 "FileVersion" "${HALY_DISPLAY_VERSION}"
VIAddVersionKey /LANG=1033 "ProductVersion" "${HALY_DISPLAY_VERSION}"

!define MUI_ABORTWARNING
!define MUI_ICON "${HALY_ICON}"
!define MUI_UNICON "${HALY_ICON}"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "Japanese"

Section "Haly Browser" SEC_MAIN
  SetShellVarContext current
  SetOutPath "$INSTDIR"

  ; Replace only this product's private installation directory. The official
  ; Brave directories and registry entries are never read or modified.
  RMDir /r "$INSTDIR\Application"
  Delete "$INSTDIR\Haly.exe"
  Delete "$INSTDIR\NOTICE-HALY.txt"

  File /r "${PAYLOAD_DIR}\*.*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  WriteRegStr HKCU "${PRODUCT_REG_KEY}" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${PRODUCT_REG_KEY}" "ProfileDir" "$LOCALAPPDATA\Haly\User Data"

  WriteRegStr HKCU "${PRODUCT_UNINSTALL_KEY}" "DisplayName" "Haly Browser"
  WriteRegStr HKCU "${PRODUCT_UNINSTALL_KEY}" "DisplayVersion" "${HALY_DISPLAY_VERSION}"
  WriteRegStr HKCU "${PRODUCT_UNINSTALL_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
  WriteRegStr HKCU "${PRODUCT_UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${PRODUCT_UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\Haly.exe"
  WriteRegStr HKCU "${PRODUCT_UNINSTALL_KEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegDWORD HKCU "${PRODUCT_UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${PRODUCT_UNINSTALL_KEY}" "NoRepair" 1

  CreateDirectory "$SMPROGRAMS\Haly"
  CreateShortcut "$SMPROGRAMS\Haly\Haly.lnk" "$INSTDIR\Haly.exe" "" "$INSTDIR\Haly.exe" 0 SW_SHOWNORMAL "" "Haly Browser"
  CreateShortcut "$SMPROGRAMS\Haly\Uninstall Haly.lnk" "$INSTDIR\Uninstall.exe"
  CreateShortcut "$DESKTOP\Haly.lnk" "$INSTDIR\Haly.exe" "" "$INSTDIR\Haly.exe" 0 SW_SHOWNORMAL "" "Haly Browser"
SectionEnd

Section "Uninstall"
  SetShellVarContext current

  ; Terminate only the renamed Haly browser executable. Official brave.exe
  ; processes are deliberately not targeted.
  nsExec::ExecToLog '"$SYSDIR\taskkill.exe" /IM haly-browser.exe /T /F'

  Delete "$DESKTOP\Haly.lnk"
  RMDir /r "$SMPROGRAMS\Haly"
  DeleteRegKey HKCU "${PRODUCT_UNINSTALL_KEY}"
  DeleteRegKey HKCU "${PRODUCT_REG_KEY}"
  RMDir /r "$INSTDIR"

  MessageBox MB_OK|MB_ICONINFORMATION "Haly was removed. Your separate Haly profile remains in:$\r$\n$LOCALAPPDATA\Haly\User Data"
SectionEnd
