# Good Hands JWT 토큰 자동 발급 스크립트
Write-Host "🔐 Good Hands JWT 토큰 자동 발급기" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 사용자 선택
Write-Host "사용자 타입을 선택하세요:" -ForegroundColor Yellow
Write-Host "1. 케어기버 (CG001)"
Write-Host "2. 가디언 (GD001)"  
Write-Host "3. 관리자 (AD001)"
Write-Host ""

$userChoice = Read-Host "선택 (1-3)"

switch ($userChoice) {
    "1" { 
        $userCode = "CG001"
        $password = "password123"
        $userName = "케어기버"
    }
    "2" { 
        $userCode = "GD001" 
        $password = "password123"
        $userName = "가디언"
    }
    "3" { 
        $userCode = "AD001"
        $password = "admin123"
        $userName = "관리자"
    }
    default {
        Write-Host "❌ 잘못된 선택입니다." -ForegroundColor Red
        exit
    }
}

Write-Host ""
Write-Host "🔄 $userName JWT 토큰 발급 중..." -ForegroundColor Green
Write-Host ""

# API 호출
$body = @{
    user_code = $userCode
    password = $password
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://ingood.kwondol.com:10007/api/auth/login" -Method Post -Body $body -ContentType "application/json"
    
    $token = $response.access_token
    $bearerToken = "Bearer $token"
    
    Write-Host "✅ 토큰 발급 성공!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 복사할 토큰 (자동으로 클립보드에 복사됨):" -ForegroundColor Yellow
    Write-Host $bearerToken -ForegroundColor White
    Write-Host ""
    
    # 클립보드에 자동 복사
    $bearerToken | Set-Clipboard
    
    Write-Host "💡 n8n 설정 방법:" -ForegroundColor Cyan
    Write-Host "1. n8n → Credentials → Create New → Generic Credential Type"
    Write-Host "2. Name: Good Hands JWT"
    Write-Host "3. Properties:"
    Write-Host "   - Name: Authorization"
    Write-Host "   - Value: (이미 클립보드에 복사됨 - Ctrl+V로 붙여넣기)"
    Write-Host ""
    Write-Host "⏰ 이 토큰은 7일간 유효합니다" -ForegroundColor Green
    
} catch {
    Write-Host "❌ 토큰 발급 실패: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "아무 키나 누르면 종료됩니다..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
