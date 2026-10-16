param([string]$PythonPath)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$orbitRoot = $PSScriptRoot
Set-Location -LiteralPath $orbitRoot
function Assert-Exit([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed (exit $LASTEXITCODE)." }
}
if (-not [Environment]::Is64BitOperatingSystem) { throw 'Windows x64 is required.' }
if ($PythonPath) {
    & $PythonPath -c "import sys,struct; assert sys.version_info[:2] == (3,12) and struct.calcsize('P') == 8, 'Python 3.12 x64 required'"
    Assert-Exit 'Python check'
    & $PythonPath -m venv "$orbitRoot\.qt-env"
} else {
    & py -3.12 -c "import struct; assert struct.calcsize('P') == 8, 'Python x64 required'"
    Assert-Exit 'Python check'
    & py -3.12 -m venv "$orbitRoot\.qt-env"
}
Assert-Exit 'Create Python environment'
$orbitPython = "$orbitRoot\.qt-env\Scripts\python.exe"
& $orbitPython -m pip install -r "$orbitRoot\requirements.txt"
Assert-Exit 'Install Python dependencies'

$nodeVersion = '24.14.0'
$nodeArchive = "node-v$nodeVersion-win-x64.zip"
$nodeBase = "https://nodejs.org/dist/v$nodeVersion"
$downloadDir = "$orbitRoot\cache\downloads"
New-Item -ItemType Directory -Force -Path $downloadDir | Out-Null
if (-not (Test-Path -LiteralPath "$orbitRoot\runtime\node\node.exe")) {
    Invoke-WebRequest "$nodeBase/$nodeArchive" -OutFile "$downloadDir\$nodeArchive" -UseBasicParsing
    $checksums = (Invoke-WebRequest "$nodeBase/SHASUMS256.txt" -UseBasicParsing).Content
    $checksumLine = ($checksums -split "`n" | Where-Object { $_.Trim().EndsWith("  $nodeArchive") })
    if (-not $checksumLine) { throw 'Node checksum was not found.' }
    $expectedHash = ($checksumLine.Trim() -split '\s+')[0]
    $actualHash = (Get-FileHash -LiteralPath "$downloadDir\$nodeArchive" -Algorithm SHA256).Hash
    if ($actualHash -ne $expectedHash) { throw 'Node archive checksum mismatch.' }
    Expand-Archive -LiteralPath "$downloadDir\$nodeArchive" -DestinationPath $downloadDir -Force
    New-Item -ItemType Directory -Force -Path "$orbitRoot\runtime\node" | Out-Null
    Copy-Item -Path "$downloadDir\node-v$nodeVersion-win-x64\*" -Destination "$orbitRoot\runtime\node" -Recurse -Force
}
$env:PATH = "$orbitRoot\runtime\node;" + $env:PATH
$env:npm_config_cache = "$orbitRoot\cache\npm"
& "$orbitRoot\runtime\node\npm.cmd" ci --prefix "$orbitRoot\tools" --no-audit --no-fund
Assert-Exit 'Install official AI clients'
foreach ($client in @(
    'tools\node_modules\@openai\codex-win32-x64\vendor\x86_64-pc-windows-msvc\bin\codex.exe',
    'tools\node_modules\@anthropic-ai\claude-code\bin\claude.exe',
    'tools\node_modules\@google\gemini-cli\bundle\gemini.js'
)) {
    if (-not (Test-Path -LiteralPath (Join-Path $orbitRoot $client))) { throw "Missing AI client: $client" }
}
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (Test-Path -LiteralPath $compiler) {
    & $compiler /nologo /target:winexe /reference:System.Windows.Forms.dll "/win32icon:$orbitRoot\assets\app-icon.ico" "/out:$orbitRoot\EnglishOrbit.exe" "$orbitRoot\launcher.cs"
    Assert-Exit 'Build launcher'
}
Write-Host 'Setup complete. Open EnglishOrbit.exe or launch.vbs.' -ForegroundColor Green
