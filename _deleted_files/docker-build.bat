@echo off
echo Good Hands Docker 빌드 및 실행 스크립트

echo.
echo 1. 기존 컨테이너 정지 및 삭제...
docker stop goodhands-backend 2>nul
docker rm goodhands-backend 2>nul

echo.
echo 2. Docker 이미지 빌드...
docker build -t goodhands-backend .

if %ERRORLEVEL% neq 0 (
    echo 빌드 실패!
    pause
    exit /b 1
)

echo.
echo 3. Docker 컨테이너 실행...
docker run -d --name goodhands-backend -p 10007:10007 -v "%CD%\uploads:/app/uploads" -v "%CD%\logs:/app/logs" goodhands-backend

if %ERRORLEVEL% neq 0 (
    echo 컨테이너 실행 실패!
    pause
    exit /b 1
)

echo.
echo 4. 컨테이너 상태 확인...
docker ps | findstr goodhands-backend

echo.
echo 5. 로그 확인 (첫 10줄)...
timeout /t 3 /nobreak >nul
docker logs goodhands-backend | head -10

echo.
echo ===== 배포 완료! =====
echo API 문서: http://localhost:10007/docs
echo 헬스체크: http://localhost:10007/health
echo.
echo 로그 실시간 보기: docker logs -f goodhands-backend
echo 컨테이너 중지: docker stop goodhands-backend
echo.
pause
