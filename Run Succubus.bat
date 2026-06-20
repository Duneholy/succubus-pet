@echo off
echo Checking requirements...

python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ========================================================
    echo ERROR: Python is not installed or not added to PATH!
    echo ========================================================
    echo Succubus Pet requires Python to run.
    echo Please download and install Python 3 from:
    echo https://www.python.org/downloads/
    echo.
    echo IMPORTANT: During installation, make sure to check the box
    echo "Add Python to PATH" at the bottom of the installer window!
    echo.
    pause
    exit /b
)

python -c "import PIL, keyboard, pystray" >nul 2>&1
if errorlevel 1 (
    echo Installing required Python libraries...
    python -m pip install Pillow keyboard pystray
)

echo Starting Succubus Pet...
start pythonw main.py
