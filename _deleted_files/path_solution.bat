@echo off
chcp 65001 >nul
cls

echo 🚀 Good Hands HTTPS 배포 솔루션
echo ================================

echo 📁 현재 한글 경로 문제로 인해 다음 방법을 제안합니다:

echo.
echo 방법 1: 영문 경로로 프로젝트 복사
echo ----------------------------------
echo 1. C:\goodhands\ 디렉토리 생성
echo 2. 현재 프로젝트를 C:\goodhands\backend\로 복사
echo 3. 복사된 경로에서 배포 실행

echo.
echo 방법 2: Docker Desktop GUI 사용
echo -------------------------------
echo 1. Docker Desktop 열기
echo 2. Compose 탭에서 docker-compose.https.yml 직접 실행

echo.
echo 방법 3: 수동 명령어 실행
echo -------------------------
echo 프로젝트 디렉토리에서 다음 명령어 실행:
echo.
echo   docker-compose -f docker-compose.https.yml down --remove-orphans
echo   docker-compose -f docker-compose.https.yml build --no-cache  
echo   docker-compose -f docker-compose.https.yml up -d
echo.

echo.
echo 🎯 권장사항: 방법 1을 사용하여 영문 경로에서 배포

echo.
echo 자동 복사 스크립트를 실행하시겠습니까? (Y/N)
set /p choice="선택: "

if /i "%choice%"=="Y" (
    echo 📂 C:\goodhands 디렉토리 생성 중...
    mkdir "C:\goodhands" 2>nul
    mkdir "C:\goodhands\backend" 2>nul
    
    echo 📋 프로젝트 파일 복사 중...
    xcopy "\\tsclient\C\Users\융합인재센터16\goodHands\backend\*" "C:\goodhands\backend\" /E /I /Y
    
    if %ERRORLEVEL% EQU 0 (
        echo ✅ 복사 완료!
        echo 📁 새 경로: C:\goodhands\backend
        echo.
        echo 이제 다음 명령어를 실행하세요:
        echo   cd C:\goodhands\backend
        echo   docker-compose -f docker-compose.https.yml up -d
        echo.
    ) else (
        echo ❌ 복사 실패! 수동으로 복사해주세요.
    )
) else (
    echo 💡 수동으로 진행해주세요!
)

pause