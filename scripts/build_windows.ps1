$ErrorActionPreference = 'Stop'
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
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --windowed --name PPView --icon assets\ppview.ico --paths src --add-data "assets/ppview.svg;assets" src\ppview\main.py
& .\.venv\Scripts\python.exe scripts\copy_notices.py dist\PPView
Copy-Item LICENSE, LICENSES\LGPL-3.0.txt, THIRD_PARTY_LICENSES.md -Destination dist\PPView
Compress-Archive -Path dist\PPView -DestinationPath dist\PPView-windows-x64.zip -Force
& .\.venv\Scripts\python.exe scripts\package_smoke.py
if ($LASTEXITCODE -ne 0) { throw 'Packaged executable smoke test failed.' }
