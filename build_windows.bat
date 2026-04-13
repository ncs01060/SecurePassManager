@echo off
echo Installing requirements...
pip install pyinstaller PyQt6 cryptography pyperclip
echo Building Windows Executable...
pyinstaller --noconfirm --onedir --windowed --name "SecurePassManager" "app.py"
echo Build Complete! Check the 'dist' folder.
pause
