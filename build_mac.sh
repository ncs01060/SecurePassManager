#!/bin/bash
echo "Preparing isolated build environment to avoid PyInstaller Unicode path issues..."
BUILD_DIR="/tmp/passmanager_build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cp app.py crypto_utils.py "$BUILD_DIR/"

cd "$BUILD_DIR"
echo "Creating temporary virtual environment in ASCII path..."
python3 -m venv venv
source venv/bin/activate

echo "Installing requirements..."
pip install pyinstaller PyQt6 cryptography pyperclip

echo "Building Mac App..."
pyinstaller --noconfirm --onedir --windowed --name "SecurePassManager" "app.py"

echo "Copying built app back to project directory..."
TARGET_DIR="/Volumes/이영민의재산/공부/대학/인공지능기초/6주차/비밀번호관리지원"
mkdir -p "$TARGET_DIR/dist"
rm -rf "$TARGET_DIR/dist/SecurePassManager.app"
cp -R "dist/SecurePassManager.app" "$TARGET_DIR/dist/"

echo "Build complete. Mac app generated successfully in dist/ folder."
