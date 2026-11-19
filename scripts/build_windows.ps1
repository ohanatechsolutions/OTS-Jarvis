# Build only on Windows x64 after explicit review of toolchain/licensing.
$ErrorActionPreference = 'Stop'
if (-not $IsWindows -and $PSVersionTable.PSEdition -eq 'Core') { throw 'Windows required' }
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
    python -m PyInstaller --noconfirm --clean --onefile --console --name 'OTS-Jarvis' --collect-data jarvis run_jarvis.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
    $exe = Join-Path (Get-Location) 'dist/OTS-Jarvis.exe'
    if (-not (Test-Path $exe)) { throw 'Expected exe missing' }
    $stream = [IO.File]::OpenRead($exe)
    try {
        if ($stream.ReadByte() -ne 0x4D -or $stream.ReadByte() -ne 0x5A) { throw 'Not a PE MZ executable' }
    } finally { $stream.Dispose() }
    Get-FileHash $exe -Algorithm SHA256 | Format-List
    Write-Output "Build generated: $exe (not an installer; unsigned; Windows UAT required)"
} finally { Pop-Location }
