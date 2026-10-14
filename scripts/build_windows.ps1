$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$distPath = Join-Path $repoRoot 'dist'
$oldApps = Get-Process -Name PPView -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -and $_.Path.StartsWith($distPath, [System.StringComparison]::OrdinalIgnoreCase)
}
foreach ($oldApp in $oldApps) {
    [void]$oldApp.CloseMainWindow()
    if (-not $oldApp.WaitForExit(10000)) { throw "Close the running packaged app before rebuilding: $($oldApp.Path)" }
}
foreach ($outputPath in @((Join-Path $repoRoot 'build'), (Join-Path $repoRoot 'dist'))) {
    if (Test-Path -LiteralPath $outputPath) {
        $resolvedOutput = (Resolve-Path -LiteralPath $outputPath).Path
        if (-not $resolvedOutput.StartsWith($repoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to clean output outside repository: $resolvedOutput"
        }
        Remove-Item -LiteralPath $resolvedOutput -Recurse -Force
    }
}
py -3.11 -m venv --clear .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
& .\.venv\Scripts\python.exe -m pip install --no-deps -e .
& .\.venv\Scripts\python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
& .\.venv\Scripts\python.exe scripts\pdfium_smoke.py
if ($LASTEXITCODE -ne 0) { throw 'PDFium smoke test failed.' }
$env:QT_QPA_PLATFORM = 'offscreen'
& .\.venv\Scripts\python.exe scripts\ui_smoke.py
if ($LASTEXITCODE -ne 0) { throw 'Qt UI rendering smoke test failed.' }
Remove-Item Env:QT_QPA_PLATFORM
& .\.venv\Scripts\python.exe scripts\write_build_info.py ppview-build.json
if ($LASTEXITCODE -ne 0) { throw 'Could not write build metadata.' }
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --windowed --name PPView --icon assets\logo\ppview.ico --paths src --add-data "assets/logo/ppview-icon.svg;assets/logo" --add-data "ppview-build.json;." src\ppview\main.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
Remove-Item -LiteralPath ppview-build.json -Force
& .\.venv\Scripts\python.exe scripts\copy_notices.py dist\PPView
Copy-Item LICENSE, LICENSES\LGPL-3.0.txt, THIRD_PARTY_LICENSES.md -Destination dist\PPView
Compress-Archive -Path dist\PPView -DestinationPath dist\PPView-windows-x64.zip -Force
& .\.venv\Scripts\python.exe scripts\package_smoke.py
if ($LASTEXITCODE -ne 0) { throw 'Packaged executable smoke test failed.' }
