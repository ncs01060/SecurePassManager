#!/bin/bash
# 이 파일이 있는 경로로 이동
cd "$(dirname "$0")"

# 가상환경 활성화 (Python 패키지 불러오기)
source venv/bin/activate

# 프로그램 실행
python3 app.py
