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
foreach ($outputPath in @((Join-Path $repoRoot 'build'))) {
    if (Test-Path -LiteralPath $outputPath) {
        $resolvedOutput = (Resolve-Path -LiteralPath $outputPath).Path
        if (-not $resolvedOutput.StartsWith($repoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to clean output outside repository: $resolvedOutput"
        }
        Remove-Item -LiteralPath $resolvedOutput -Recurse -Force
    }
}
if (Test-Path -LiteralPath (Join-Path $distPath 'PPView')) {
    $oldPackage = Join-Path $distPath 'PPView'
    $oldVersion = 'unknown'
    $oldMetadata = Join-Path $oldPackage '_internal\ppview-build.json'
    if (Test-Path -LiteralPath $oldMetadata) {
        try { $oldVersion = (Get-Content -LiteralPath $oldMetadata -Raw | ConvertFrom-Json).version }
        catch { $oldVersion = 'unknown' }
    }
    $preserved = Join-Path $distPath "PPView-preserved-v$oldVersion"
    if (Test-Path -LiteralPath $preserved) {
        $preserved = Join-Path $distPath "PPView-preserved-v$oldVersion-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    }
    Move-Item -LiteralPath $oldPackage -Destination $preserved
}
py -3.11 -m venv --clear .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
& .\.venv\Scripts\python.exe -m pip install --no-deps -e .
& .\.venv\Scripts\python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
& .\.venv\Scripts\python.exe scripts\pdfium_diagnostics.py
if ($LASTEXITCODE -ne 0) { throw 'PDFium diagnostic matrix failed.' }
& .\.venv\Scripts\python.exe scripts\pdfium_smoke.py
if ($LASTEXITCODE -ne 0) { throw 'PDFium smoke test failed.' }
$env:QT_QPA_PLATFORM = 'offscreen'
& .\.venv\Scripts\python.exe scripts\ui_smoke.py
if ($LASTEXITCODE -ne 0) { throw 'Qt UI rendering smoke test failed.' }
& .\.venv\Scripts\python.exe scripts\help_screenshot_smoke.py
if ($LASTEXITCODE -ne 0) { throw 'Localized help dialog screenshot smoke test failed.' }
& .\.venv\Scripts\python.exe scripts\zoom_benchmark.py --output dist\zoom-benchmark.json
if ($LASTEXITCODE -ne 0) { throw 'Zoom performance benchmark failed.' }
Remove-Item Env:QT_QPA_PLATFORM
& .\.venv\Scripts\python.exe scripts\write_build_info.py ppview-build.json
if ($LASTEXITCODE -ne 0) { throw 'Could not write build metadata.' }
$appVersion = (Get-Content ppview-build.json -Raw | ConvertFrom-Json).display_version
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --windowed --name PPView --icon assets\logo\ppview.ico --version-file build\version_info.txt --paths src --additional-hooks-dir scripts\pyinstaller_hooks --add-data "assets/logo/ppview-icon.svg;assets/logo" --add-data "assets/logo/ppview.ico;assets/logo" --add-data "ppview-build.json;." src\ppview\main.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
Remove-Item -LiteralPath ppview-build.json -Force
& .\.venv\Scripts\python.exe scripts\copy_notices.py dist\PPView
Copy-Item LICENSE, LICENSES\LGPL-3.0.txt, THIRD_PARTY_LICENSES.md -Destination dist\PPView
Compress-Archive -Path dist\PPView -DestinationPath "dist\PPView-Portable-v$appVersion-x64.zip" -Force
& .\.venv\Scripts\python.exe scripts\package_smoke.py
if ($LASTEXITCODE -ne 0) { throw 'Packaged executable smoke test failed.' }
$innoPath = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
if (-not $innoPath) {
    foreach ($candidate in @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
                             "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
                             "$env:ProgramFiles\Inno Setup 6\ISCC.exe")) {
        if (Test-Path -LiteralPath $candidate) { $innoPath = $candidate; break }
    }
}
if (-not $innoPath) { throw 'Install Inno Setup 6 to build the Windows installer.' }
& $innoPath installer\PPView.iss
if ($LASTEXITCODE -ne 0) { throw 'Inno Setup compilation failed.' }
& .\.venv\Scripts\python.exe scripts\installer_smoke.py
if ($LASTEXITCODE -ne 0) { throw 'Installer install/uninstall smoke test failed.' }
Get-FileHash "dist\PPView-Portable-v$appVersion-x64.zip", "dist\PPView-Setup-v$appVersion-x64.exe" -Algorithm SHA256 | ForEach-Object {
    "$($_.Hash.ToLower())  $([IO.Path]::GetFileName($_.Path))"
} | Set-Content -Encoding ascii dist\SHA256SUMS.txt
