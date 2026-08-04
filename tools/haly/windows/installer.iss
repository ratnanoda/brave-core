#define MyAppName "Haly Browser"
#define MyAppVersion GetEnv("HALY_DISPLAY_VERSION")
#define MyAppFileVersion GetEnv("HALY_FILE_VERSION")
#define MyPayloadDir GetEnv("HALY_PAYLOAD")
#define MyOutputDir GetEnv("HALY_OUTPUT")
#define MyIconFile GetEnv("HALY_ICON")

[Setup]
AppId={{6B94C2EC-3443-4B23-9A36-2B8A1C751208}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=Haly Authors
AppPublisherURL=https://github.com/ratnanoda/brave-core
AppSupportURL=https://github.com/ratnanoda/brave-core/pull/2
AppUpdatesURL=https://github.com/ratnanoda/brave-core/pull/2
VersionInfoVersion={#MyAppFileVersion}
VersionInfoCompany=Haly Authors
VersionInfoDescription=Haly Browser Offline Installer
VersionInfoProductName=Haly Browser
VersionInfoProductVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\Haly
DefaultGroupName=Haly
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#MyOutputDir}
OutputBaseFilename=HalySetup-x64
SetupIconFile={#MyIconFile}
UninstallDisplayIcon={app}\Haly.exe
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes
UsePreviousGroup=yes
ChangesAssociations=no
CreateUninstallRegKey=yes
Uninstallable=yes
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#MyPayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{localappdata}\Haly\User Data"; Flags: uninsneveruninstall

[Icons]
Name: "{group}\Haly"; Filename: "{app}\Haly.exe"; WorkingDir: "{app}"; Comment: "Haly Browser"
Name: "{group}\Uninstall Haly"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Haly"; Filename: "{app}\Haly.exe"; WorkingDir: "{app}"; Tasks: desktopicon; Comment: "Haly Browser"

[Registry]
Root: HKCU; Subkey: "Software\Haly"; ValueType: string; ValueName: "InstallDir"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Haly"; ValueType: string; ValueName: "ProfileDir"; ValueData: "{localappdata}\Haly\User Data"

[Run]
Filename: "{app}\Haly.exe"; Description: "Launch Haly Browser"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/IM haly-browser.exe /T /F"; Flags: runhidden waituntilterminated; RunOnceId: "StopHalyBrowser"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
