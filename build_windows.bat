@echo off
echo ======================================================
echo  Secure Password Manager - Windows Build Script
echo ======================================================

:: 1. Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed. Please install Python to continue.
    pause
    exit /b
)

:: 2. Create Virtual Environment
echo [1/4] Creating virtual environment...
python -m venv venv_win
call venv_win\Scripts\activate

:: 3. Install Dependencies
echo [2/4] Installing dependencies...
pip install --upgrade pip
pip install pyinstaller PyQt6 cryptography pyperclip

:: 4. Build Executable
echo [3/4] Building Windows Executable (.exe)...
:: --noconfirm: overwrites existing dist
:: --onefile: packages everything into a single .exe
:: --windowed: no terminal window shows up when running the app
:: --icon: if you have an .ico file, add --icon="icon.ico"
pyinstaller --noconfirm --onefile --windowed --name "SecurePassManager_Win" "app.py"

:: 5. Cleanup
echo [4/4] Cleaning up temporary files...
deactivate
echo.
echo ======================================================
echo  Build Complete! 
echo  The executable is located in: dist\SecurePassManager_Win.exe
echo ======================================================
pause

