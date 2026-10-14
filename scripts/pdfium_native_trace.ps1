$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$candidate = Get-Command cdb.exe -ErrorAction SilentlyContinue
if ($candidate) { $cdb = $candidate.Source }
else {
    $candidate = Get-ChildItem 'C:\Program Files\Windows Kits\10\Debuggers\x64\cdb.exe' -ErrorAction SilentlyContinue
    if (-not $candidate) {
        $candidate = Get-ChildItem 'C:\Program Files\WindowsApps\Microsoft.WinDbg_*_x64__8wekyb3d8bbwe\amd64\cdb.exe' -ErrorAction SilentlyContinue |
            Select-Object -First 1
    }
    if (-not $candidate) { throw 'CDB was not found. Install Debugging Tools for Windows (WinDbg).'; }
    $cdb = $candidate.FullName
}

$python = (& py -3.11 -c 'import sys; print(sys.executable)').Trim()
if (-not (Test-Path -LiteralPath $python)) { throw "CPython 3.11 was not found: $python" }
$env:PYTHONPATH = (Join-Path $repoRoot '.venv\Lib\site-packages') + ';' + (Join-Path $repoRoot 'src')
$log = Join-Path $repoRoot 'build\pdfium-native-trace.log'
New-Item -ItemType Directory -Path (Split-Path $log) -Force | Out-Null
$commands = 'sxe -c ".echo === FIRST-CHANCE ACCESS VIOLATION ===; .exr -1; kv; lmvm TmUmEvt64; sxd av; g" av; g'
& $cdb -logo $log -c $commands $python -c 'import pypdfium2'
$debuggerExit = $LASTEXITCODE
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
Write-Output "CDB log: $log"
Write-Output "CDB exit code: $debuggerExit"
$trace = Get-Content -LiteralPath $log -Raw
if ($debuggerExit -ne 0 -and -not $trace.Contains('FIRST-CHANCE ACCESS VIOLATION')) {
    throw 'CDB failed before capturing an access violation.'
}
