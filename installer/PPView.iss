#define AppName "PPView"
#define AppPublisher "Matthieu Tuffet"
#include "version.iss"

[Setup]
AppId={{B2F1B84C-2A6A-4D31-9F88-8C6A7D22C2A0}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\PPView
DefaultGroupName=PPView
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename=PPView-Setup-v{#AppVersion}-x64
SetupIconFile=..\assets\logo\ppview.ico
UninstallDisplayIcon={app}\PPView.exe
UninstallDisplayName=PPView
VersionInfoVersion={#AppNumericVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=PPView Windows Installer
VersionInfoProductName=PPView
LicenseFile=..\LICENSE
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ChangesAssociations=no
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\PPView\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSES\LGPL-3.0.txt"; DestDir: "{app}\licenses"; Flags: ignoreversion
Source: "..\THIRD_PARTY_LICENSES.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\PPView"; Filename: "{app}\PPView.exe"; IconFilename: "{app}\PPView.exe"
Name: "{autodesktop}\PPView"; Filename: "{app}\PPView.exe"; IconFilename: "{app}\PPView.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\PPView.exe"; Description: "Launch PPView"; Flags: postinstall nowait skipifsilent
