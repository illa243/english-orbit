param([ValidateSet('ChatGPT','Claude','Gemini')][string]$Provider)
$ErrorActionPreference = 'Stop'
$orbitRoot = $PSScriptRoot
Write-Host "English Orbit - official $Provider sign-in" -ForegroundColor Cyan
Write-Host 'Choose subscription / Google sign-in. Do not select API billing.'
if ($Provider -eq 'ChatGPT') {
    & "$orbitRoot\tools\node_modules\@openai\codex-win32-x64\vendor\x86_64-pc-windows-msvc\bin\codex.exe" login
} elseif ($Provider -eq 'Claude') {
    & "$orbitRoot\tools\node_modules\@anthropic-ai\claude-code\bin\claude.exe" auth login
} else {
    & "$orbitRoot\runtime\node\node.exe" "$orbitRoot\tools\node_modules\@google\gemini-cli\bundle\gemini.js"
}
Write-Host 'English Orbit detects sign-in and refreshes models automatically.'
Read-Host 'Press Enter to close'
