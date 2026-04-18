#!/bin/bash
# 1. 현재 디렉토리 저장
PROJECT_ROOT=$(pwd)

echo "Preparing build environment..."
# 임시 빌드 디렉토리 생성 (한글 경로 문제 방지용)
BUILD_DIR="/tmp/passmanager_build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# 2. 필수 파일 복사 (icons 폴더 포함)
cp app.py crypto_utils.py requirements.txt "$BUILD_DIR/"
cp -R icons "$BUILD_DIR/" 2>/dev/null || mkdir -p "$BUILD_DIR/icons"

cd "$BUILD_DIR"

# 3. 가상환경 세팅 및 의존성 설치
echo "Creating temporary virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Installing requirements..."
pip install --upgrade pip
pip install pyinstaller PyQt6 cryptography pyperclip

# 4. PyInstaller 실행 (윈도우 모드)
echo "Building Mac App..."
pyinstaller --noconfirm --onedir --windowed \
    --name "SecurePassManager" \
    --add-data "icons:icons" \
    "app.py"

# 5. 결과물을 현재 프로젝트의 dist 폴더로 이동
echo "Moving built app to project directory..."
rm -rf "$PROJECT_ROOT/dist"
mkdir -p "$PROJECT_ROOT/dist"
cp -R "dist/SecurePassManager.app" "$PROJECT_ROOT/dist/"

echo "-----------------------------------------------"
echo "✅ Build Complete!"
echo "Location: $PROJECT_ROOT/dist/SecurePassManager.app"
echo "-----------------------------------------------"
