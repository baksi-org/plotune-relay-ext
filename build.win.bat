@echo off
setlocal enabledelayedexpansion

echo ==================================================
echo Plotune relay Extension Builder
echo ==================================================

:: Activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo Virtual environment not found. Creating .venv...
    python -m venv .venv
    call .venv\Scripts\activate.bat
)

:: Install requirements
echo Installing Python dependencies...
pip install --upgrade pip
if exist "requirements.txt" (
    pip install -r requirements.txt
)

:: Ensure PyInstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
)

:: Set variables
set ZIP_NAME=plotune-relay-ext-windows-x86_64.zip
set DIST_DIR=dist
set HISTORY_DIR=%DIST_DIR%\history

:: Create history folder if missing
if not exist "%HISTORY_DIR%" mkdir "%HISTORY_DIR%"

:: Move previous zip to history if exists
if exist "%DIST_DIR%\%ZIP_NAME%" (
    for /f "tokens=1-6 delims=/:. " %%a in ("%date% %time%") do (
        set DATE_TAG=%%c%%a%%b_%%d%%e%%f
    )
    echo Moving existing ZIP to history: !DATE_TAG!
    move "%DIST_DIR%\%ZIP_NAME%" "%HISTORY_DIR%\%ZIP_NAME%_!DATE_TAG!"
)

:: Build executable
echo Building executable...
pyinstaller --name plotune_relay_ext ^
            --onedir ^
            --noconfirm ^
            --icon assets/logo.ico ^
            src\main.py

:: Copy plugin.json
echo Copying plugin.json to build directory...
copy src\plugin.json dist\plotune_relay_ext\plugin.json /Y

:: Patch plugin.json for Windows executable
echo Patching plugin.json cmd field for Windows build...

powershell -NoProfile -Command "$p='dist\plotune_relay_ext\plugin.json'; $json=Get-Content $p -Raw | ConvertFrom-Json; $json.cmd=@('plotune_relay_ext.exe'); $json | ConvertTo-Json -Depth 10 | Set-Content $p -Encoding UTF8"


:: Create ZIP archive
echo Creating ZIP archive...
cd dist

powershell -NoProfile -Command "Compress-Archive -Path 'plotune_relay_ext\*' -DestinationPath '%ZIP_NAME%' -Force"

certutil -hashfile %ZIP_NAME% SHA256 | findstr /v "hash" > %ZIP_NAME%.sha256

cd ..


echo ==================================================
echo Build and ZIP completed successfully!
echo ==================================================
pause