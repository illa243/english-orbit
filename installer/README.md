# Windows release build

Build on Windows x64 with the project's dependencies installed (see `setup.ps1`)
and a standalone, relocatable CPython 3.12 base distribution.

1. Install the signed Inno Setup compiler from https://jrsoftware.org/isdl.php.
2. Run `build_payload.py --dependencies <dependency-install-folder> --output <new-payload-folder>`.
   It copies an explicit module/asset allowlist and library packages only.
3. Compile `launcher.cs` using .NET Framework `csc.exe`, `/target:winexe`,
   `/reference:System.Windows.Forms.dll`, `/win32icon:assets/app-icon.ico`,
   and `/out:<payload-folder>/EnglishOrbit.exe`.
4. Run `ISCC.exe /DPayloadDir=<payload-folder> /DOutputDir=<release-folder> EnglishOrbit.iss`.
5. Test installation to a fresh folder and run its bundled Python with
   `main.py --demo --smoke --screenshot <test-output-path>`.
   Check each bundled official client's `--version` without authenticating.
6. Verify no `data`, `cache`, auth tokens, private databases or custom characters
   appear in the payload before uploading the installer. Publish its SHA-256 hash.

The installer installs per user without elevation and preserves user-created
data on update/uninstall. Default agent instructions are installed only when
missing. Application dependencies are bundled, not downloaded during installation.
AI account sign-in and conversations still require internet access.

The executable is not code-signed. Do not describe it as signed or verified by
Microsoft. Testing a fresh install folder does not replace testing on a clean VM.
