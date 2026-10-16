#ifndef PayloadDir
  #error PayloadDir must point to the audited clean package
#endif
#ifndef OutputDir
  #define OutputDir "."
#endif
#define AppVersion "0.2.0"
[Setup]
AppId={{809A58A1-74D0-45D0-B9C4-FBA1D73829BD}
AppName=English Orbit
AppVersion={#AppVersion}
AppPublisher=English Orbit
AppPublisherURL=https://github.com/illa243/english-orbit
DefaultDirName={localappdata}\Programs\English Orbit
DefaultGroupName=English Orbit
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
WizardStyle=modern
SetupIconFile={#PayloadDir}\assets\app-icon.ico
UninstallDisplayIcon={app}\EnglishOrbit.exe
OutputDir={#OutputDir}
OutputBaseFilename=EnglishOrbit-Setup-0.2.0-win-x64
Compression=lzma2/normal
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
UninstallDisplayName=English Orbit
DisableWelcomePage=no

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; Flags: checkedonce

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Excludes: "agents\*"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#PayloadDir}\agents\*"; DestDir: "{app}\agents"; Flags: onlyifdoesntexist uninsneveruninstall

[Icons]
Name: "{group}\English Orbit"; Filename: "{app}\EnglishOrbit.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\English Orbit"; Filename: "{app}\EnglishOrbit.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\EnglishOrbit.exe"; Description: "Launch English Orbit"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "EnglishOrbit"; Flags: uninsdeletevalue
