; Inno Setup script — builds ApexSteelSearch-Setup-x.y.z.exe
; Compile:  ISCC.exe /DMyAppVersion=0.1.0 packaging\installer.iss
#ifndef MyAppVersion
  #define MyAppVersion "0.1.0"
#endif

[Setup]
AppId={{6F3A2C1E-8B4D-4E7A-9C21-5D0B7A1E3F42}
AppName=Apex Steel Analyser
AppVersion={#MyAppVersion}
AppPublisher=Apex Steel
DefaultDirName={autopf}\Apex Steel Analyser
DefaultGroupName=Apex Steel Analyser
DisableProgramGroupPage=yes
OutputDir=..\Output
OutputBaseFilename=ApexSteelSearch-Setup-{#MyAppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\ApexSteelSearch.exe
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\ApexSteelSearch\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[InstallDelete]
; remove the old shortcut names from v0.1.x
Type: files; Name: "{autodesktop}\Apex Steel Search.lnk"
Type: files; Name: "{autoprograms}\Apex Steel Search.lnk"

[Icons]
Name: "{autoprograms}\Apex Steel Analyser"; Filename: "{app}\ApexSteelSearch.exe"
Name: "{autodesktop}\Apex Steel Analyser"; Filename: "{app}\ApexSteelSearch.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ApexSteelSearch.exe"; Description: "{cm:LaunchProgram,Apex Steel Analyser}"; Flags: nowait postinstall skipifsilent
