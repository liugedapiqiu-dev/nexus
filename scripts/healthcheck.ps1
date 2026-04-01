# healthcheck.ps1 - 健康检查脚本
# 用法: .\healthcheck.ps1

param([switch]$Verbose)

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "阿豪 AI Brain - 健康检查" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$allPassed = $true

# 1. Node.js
Write-Host "[1/10] Node.js..." -ForegroundColor Yellow
if (Get-Command node -ErrorAction SilentlyContinue) {
    $version = node --version
    Write-Host "  [OK] Node.js $version" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Node.js 未安装" -ForegroundColor Red
    $allPassed = $false
}

# 2. Python
Write-Host "[2/10] Python..." -ForegroundColor Yellow
if (Get-Command python -ErrorAction SilentlyContinue) {
    $version = python --version
    Write-Host "  [OK] Python $version" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Python 未安装" -ForegroundColor Red
    $allPassed = $false
}

# 3. Ollama CLI
Write-Host "[3/10] Ollama CLI..." -ForegroundColor Yellow
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Write-Host "  [OK] Ollama 已安装" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Ollama 未安装" -ForegroundColor Red
    $allPassed = $false
}

# 4. Ollama 服务
Write-Host "[4/10] Ollama 服务..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "  [OK] Ollama 服务运行中" -ForegroundColor Green
    }
} catch {
    Write-Host "  [WARN] Ollama 服务未运行 (请运行 'ollama serve')" -ForegroundColor Yellow
}

# 5. 目录结构
Write-Host "[5/10] 目录结构..." -ForegroundColor Yellow
$requiredDirs = @(
    "$env:USERPROFILE\.vectorbrain",
    "$env:USERPROFILE\.openclaw",
    "$env:USERPROFILE\.openclaw\workspace",
    "$env:USERPROFILE\.vectorbrain\connector",
    "$env:USERPROFILE\.openclaw\hooks"
)
$dirsOk = $true
foreach ($dir in $requiredDirs) {
    if (Test-Path $dir) {
        if ($Verbose) { Write-Host "  [OK] $dir" -ForegroundColor Green }
    } else {
        Write-Host "  [FAIL] 缺少: $dir" -ForegroundColor Red
        $dirsOk = $false
        $allPassed = $false
    }
}
if ($dirsOk) { Write-Host "  [OK] 目录结构完整" -ForegroundColor Green }

# 6. 核心文件
Write-Host "[6/10] 核心文件..." -ForegroundColor Yellow
$coreFiles = @(
    "$env:USERPROFILE\.vectorbrain\config.yaml",
    "$env:USERPROFILE\.vectorbrain\connector\nexus_bootstrap.py",
    "$env:USERPROFILE\.openclaw\workspace\IDENTITY.md",
    "$env:USERPROFILE\.openclaw\workspace\SOUL.md",
    "$env:USERPROFILE\.openclaw\hooks\on-start.ps1"
)
$filesOk = $true
foreach ($f in $coreFiles) {
    if (Test-Path $f) {
        if ($Verbose) { Write-Host "  [OK] $(Split-Path $f -Leaf)" -ForegroundColor Green }
    } else {
        Write-Host "  [WARN] 缺少: $(Split-Path $f -Leaf)" -ForegroundColor Yellow
        $filesOk = $false
    }
}
if ($filesOk) { Write-Host "  [OK] 核心文件完整" -ForegroundColor Green }

# 7. Python 包
Write-Host "[7/10] Python 包..." -ForegroundColor Yellow
$requiredPyPkgs = @("faiss", "pyautogui", "pandas")
$pyPkgsOk = $true
foreach ($pkg in $requiredPyPkgs) {
    $installed = pip show $pkg 2>&1
    if ($installed -match "Name:") {
        if ($Verbose) { Write-Host "  [OK] $pkg" -ForegroundColor Green }
    } else {
        Write-Host "  [FAIL] Python 包缺失: $pkg" -ForegroundColor Red
        $pyPkgsOk = $false
        $allPassed = $false
    }
}
if ($pyPkgsOk) { Write-Host "  [OK] Python 依赖完整" -ForegroundColor Green }

# 8. VectorBrain API
Write-Host "[8/10] VectorBrain API..." -ForegroundColor Yellow
$apiPath = "$env:USERPROFILE\.vectorbrain\connector\api_server.py"
if (Test-Path $apiPath) {
    Write-Host "  [OK] api_server.py 存在" -ForegroundColor Green
} else {
    Write-Host "  [WARN] api_server.py 不存在" -ForegroundColor Yellow
}

# 9. 启动钩子
Write-Host "[9/10] 启动钩子..." -ForegroundColor Yellow
$hookPath = "$env:USERPROFILE\.openclaw\hooks\on-start.ps1"
if (Test-Path $hookPath) {
    Write-Host "  [OK] 启动钩子存在" -ForegroundColor Green
} else {
    Write-Host "  [WARN] 启动钩子不存在" -ForegroundColor Yellow
}

# 10. 记忆数据库
Write-Host "[10/10] 记忆数据库..." -ForegroundColor Yellow
$memoryDir = "$env:USERPROFILE\.vectorbrain\memory"
if (Test-Path $memoryDir) {
    $dbFiles = Get-ChildItem -Path $memoryDir -Filter "*.db" -ErrorAction SilentlyContinue
    if ($dbFiles) {
        Write-Host "  [OK] $($dbFiles.Count) 个数据库文件" -ForegroundColor Green
    } else {
        Write-Host "  [INFO] 数据库文件将在首次启动时创建" -ForegroundColor Gray
    }
} else {
    Write-Host "  [WARN] memory 目录不存在" -ForegroundColor Yellow
}

# 总结
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($allPassed) {
    Write-Host "所有检查通过! 系统已就绪." -ForegroundColor Green
} else {
    Write-Host "部分检查未通过，请安装缺失的组件." -ForegroundColor Yellow
}
Write-Host "========================================" -ForegroundColor Cyan
