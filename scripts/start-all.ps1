# start-all.ps1 - 启动所有服务
param([switch]$SkipOllama, [switch]$SkipGateway)

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "阿豪 AI Brain - 启动所有服务" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Ollama
if (-not $SkipOllama) {
    Write-Host "[1/3] Ollama..." -ForegroundColor Yellow
    $ollamaRunning = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
    if ($ollamaRunning) {
        Write-Host "  [INFO] Ollama 已在运行" -ForegroundColor Gray
    } else {
        Write-Host "  [INFO] 启动 Ollama..." -ForegroundColor Gray
        Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 2
        Write-Host "  [OK] Ollama 已启动" -ForegroundColor Green
    }
}

# 2. VectorBrain API
Write-Host "[2/3] VectorBrain API..." -ForegroundColor Yellow
$apiPath = "$env:USERPROFILE\.vectorbrain\connector\api_server.py"
if (Test-Path $apiPath) {
    Start-Process -FilePath "python" -ArgumentList $apiPath -WindowStyle Hidden
    Write-Host "  [OK] VectorBrain API 已启动 (port 9000)" -ForegroundColor Green
} else {
    Write-Host "  [WARN] api_server.py 不存在，跳过" -ForegroundColor Yellow
}

# 3. OpenClaw Gateway
if (-not $SkipGateway) {
    Write-Host "[3/3] OpenClaw Gateway..." -ForegroundColor Yellow
    Write-Host "  [INFO] 请参考 OpenClaw 文档手动启动 gateway --port 18789" -ForegroundColor Gray
}

# 4. 运行启动钩子
Write-Host ""
Write-Host "[钩子] 执行启动钩子..." -ForegroundColor Yellow
$hookPath = "$env:USERPROFILE\.openclaw\hooks\on-start.ps1"
if (Test-Path $hookPath) {
    & $hookPath
    Write-Host "  [OK] 启动钩子执行完成" -ForegroundColor Green
} else {
    Write-Host "  [WARN] 启动钩子不存在" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "服务启动完成!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "服务地址:" -ForegroundColor Yellow
Write-Host "  Ollama:           http://127.0.0.1:11434" -ForegroundColor White
Write-Host "  VectorBrain API:  http://127.0.0.1:9000" -ForegroundColor White
Write-Host "  OpenClaw Gateway: http://127.0.0.1:18789" -ForegroundColor White
Write-Host ""
