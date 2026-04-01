# install-deps.ps1 - 依赖安装脚本
param([switch]$PythonOnly, [switch]$NodeOnly)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "阿豪 AI Brain - 依赖安装" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$pythonPackages = @(
    "faiss-cpu",
    "pyautogui",
    "pillow",
    "opencv-python",
    "pygetwindow",
    "pandas",
    "numpy",
    "yfinance",
    "pypika"
)

$nodePackages = @(
    "@vercel/agent-browser"
)

if (-not $NodeOnly) {
    Write-Host "[1/2] 安装 Python 包..." -ForegroundColor Yellow
    Write-Host ""
    python -m pip install --upgrade pip
    foreach ($pkg in $pythonPackages) {
        Write-Host "  安装 $pkg..." -ForegroundColor Gray
        pip install $pkg 2>&1 | Out-Null
    }
    Write-Host ""
    Write-Host "Python 包安装完成!" -ForegroundColor Green
}

if (-not $PythonOnly) {
    Write-Host "[2/2] 安装 Node.js 包..." -ForegroundColor Yellow
    Write-Host ""
    foreach ($pkg in $nodePackages) {
        Write-Host "  安装 $pkg..." -ForegroundColor Gray
        npm install -g $pkg 2>&1 | Out-Null
    }
    Write-Host ""
    Write-Host "Node.js 包安装完成!" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "依赖安装完成!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
