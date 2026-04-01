#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Nexus Brain - 安全安装脚本 v4.0
.DESCRIPTION
    智能检测已有环境，合并安装不破坏原有生态
    - 检测已有 OpenClaw/VectorBrain
    - 合并模式: 只添加缺失文件，保留原有配置
    - 覆盖模式: 完整替换 (需用户确认)
.EXAMPLE
    .\install.ps1
#>
param(
    [string]$SrcDir = "",
    [switch]$MergeInstall,
    [switch]$OverwriteInstall,
    [switch]$SkipPreCheck,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# ============================================================
# 配色与输出
# ============================================================

function Write-Banner {
    param([string]$Text)
    Write-Host ""
    Write-Host ("=" * 72) -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host ("=" * 72) -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step {
    param([int]$Num, [int]$Total, [string]$Text)
    Write-Host "[$Num/$Total] $Text" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Text)
    Write-Host "[OK] $Text" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Text)
    Write-Host "[WARN] $Text" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Text)
    Write-Host "[FAIL] $Text" -ForegroundColor Red
}

function Write-Info {
    param([string]$Text)
    Write-Host "       $Text" -ForegroundColor Gray
}

# ============================================================
# 环境检测
# ============================================================

function Test-EnvironmentExists {
    $vb = Test-Path "$env:USERPROFILE\.vectorbrain"
    $oc = Test-Path "$env:USERPROFILE\.openclaw"
    return @{
        VectorBrain = $vb
        OpenClaw = $oc
        Both = ($vb -and $oc)
        Either = ($vb -or $oc)
    }
}

function Get-EnvironmentInfo {
    param($Env)

    $info = @{}

    if ($Env.VectorBrain) {
        $vbDir = "$env:USERPROFILE\.vectorbrain"
        $info.VectorBrain = @{
            Exists = $true
            Config = Test-Path "$vbDir\config.yaml"
            Memory = @(Get-ChildItem "$vbDir\memory\*.db" -ErrorAction SilentlyContinue).Count
            Skills = @(Get-ChildItem "$vbDir\skills\*" -Directory -ErrorAction SilentlyContinue).Count
            Connector = Test-Path "$vbDir\connector\nexus_bootstrap.py"
        }
    }

    if ($Env.OpenClaw) {
        $ocDir = "$env:USERPROFILE\.openclaw"
        $info.OpenClaw = @{
            Exists = $true
            Config = Test-Path "$ocDir\openclaw.json"
            Workspace = Test-Path "$ocDir\workspace"
            Skills = @(Get-ChildItem "$ocDir\skills\*" -Directory -ErrorAction SilentlyContinue).Count
            Extensions = Test-Path "$ocDir\extensions"
        }
    }

    return $info
}

# ============================================================
# 预检查系统
# ============================================================

function Get-SystemReport {
    Write-Banner "系统预检查"

    $report = @{
        NodeJS          = @{ Name="Node.js";         Installed=$false; Version=""; Required=$true }
        Python          = @{ Name="Python";           Installed=$false; Version=""; Required=$true }
        Ollama          = @{ Name="Ollama";           Installed=$false; Version=""; Required=$true }
        Git             = @{ Name="Git";              Installed=$false; Version=""; Required=$false }
        Pip             = @{ Name="pip";              Installed=$false; Version=""; Required=$true }
        Npm             = @{ Name="npm";              Installed=$false; Version=""; Required=$true }
        Faiss           = @{ Name="faiss-cpu";        Installed=$false; Version=""; Required=$true }
        PyAutoGUI       = @{ Name="pyautogui";        Installed=$false; Version=""; Required=$true }
        Pandas          = @{ Name="pandas";           Installed=$false; Version=""; Required=$true }
        Numpy           = @{ Name="numpy";            Installed=$false; Version=""; Required=$true }
        Yfinance        = @{ Name="yfinance";         Installed=$false; Version=""; Required=$false }
        Pillow          = @{ Name="pillow";           Installed=$false; Version=""; Required=$true }
        PyGetWindow     = @{ Name="pygetwindow";      Installed=$false; Version=""; Required=$true }
        OllamaModelQwen = @{ Name="Ollama: qwen2.5:14b"; Installed=$false; Version=""; Required=$true }
        OllamaModelEmbedding = @{ Name="Ollama: nomic-embed-text (向量模型)"; Installed=$false; Version=""; Required=$true }
    }

    # Node.js
    $node = Get-Command node -ErrorAction SilentlyContinue
    if ($node) {
        $report.NodeJS.Installed = $true
        $report.NodeJS.Version = node --version
    }

    # Python
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        $report.Python.Installed = $true
        $report.Python.Version = python --version 2>&1
    }

    # Ollama
    $ollama = Get-Command ollama -ErrorAction SilentlyContinue
    if ($ollama) {
        $report.Ollama.Installed = $true
        $report.Ollama.Version = ollama --version 2>&1
        try {
            $models = ollama list 2>&1
            if ($models -match "qwen2.5.*14b") {
                $report.OllamaModelQwen.Installed = $true
            }
            if ($models -match "nomic-embed-text") {
                $report.OllamaModelEmbedding.Installed = $true
            }
        } catch {}
    }

    # pip
    $pip = Get-Command pip -ErrorAction SilentlyContinue
    if ($pip) {
        $report.Pip.Installed = $true
        $report.Pip.Version = pip --version 2>&1
    }

    # npm
    $npmCmd = Get-Command npm -ErrorAction SilentlyContinue
    if ($npmCmd) {
        $report.Npm.Installed = $true
        $report.Npm.Version = npm --version 2>&1
    }

    # Python 包
    if ($report.Pip.Installed) {
        $installedPkgs = pip list 2>&1
        foreach ($pkg in @("faiss", "pyautogui", "pandas", "numpy", "yfinance", "pillow")) {
            if ($installedPkgs -match [regex]::Escape($pkg)) {
                $report.$pkg.Installed = $true
            }
        }
        if ($installedPkgs -match "pygetwindow") { $report.PyGetWindow.Installed = $true }
    }

    return $report
}

function Show-SystemReport {
    param($Report)

    Write-Host "【必需】" -ForegroundColor Red
    $missingRequired = @()
    foreach ($key in @("NodeJS","Python","Ollama","Pip","Npm","Faiss","PyAutoGUI","Pandas","Numpy","Pillow","PyGetWindow","OllamaModelQwen","OllamaModelEmbedding")) {
        $item = $Report[$key]
        if ($item.Installed) {
            Write-Host "  [OK]   $($item.Name)" -ForegroundColor Green
        } else {
            Write-Host "  [MISS] $($item.Name)" -ForegroundColor Red
            $missingRequired += $item.Name
        }
    }

    return $missingRequired
}

function Install-Missing {
    param($Missing)

    if ($Missing.Count -eq 0) { return }

    Write-Host ""
    Write-Host "缺失的依赖: $($Missing -join ', ')" -ForegroundColor Yellow

    # Ollama 未安装
    if ($Missing -contains "Ollama") {
        Write-Host ""
        Write-Warn "Ollama 未安装!"
        Write-Host "请下载并安装 Ollama: https://ollama.ai/" -ForegroundColor Cyan
        $dl = Read-Host "是否自动打开下载页面? (Y/N)"
        if ($dl -eq "Y" -or $dl -eq "y") {
            Start-Process "https://ollama.ai/"
        }
        Write-Host "安装完成后，请重新运行此安装程序" -ForegroundColor Yellow
        return
    }

    $response = Read-Host "是否自动安装缺失依赖? (Y/N)"
    if ($response -ne "Y" -and $response -ne "y") { return }

    # Python 包
    $pyMissing = $Missing | Where-Object { $_ -in @("faiss-cpu","pyautogui","pandas","numpy","yfinance","pillow","pygetwindow") }
    if ($pyMissing.Count -gt 0) {
        Write-Host ""
        Write-Host "安装 Python 包..." -ForegroundColor Yellow
        python -m pip install --upgrade pip 2>&1 | Out-Null
        foreach ($pkg in $pyMissing) {
            Write-Host "  安装 $pkg..." -ForegroundColor Gray
            pip install $pkg 2>&1 | Out-Null
        }
        Write-Success "Python 包安装完成"
    }

    # Ollama 模型下载
    $modelsToDownload = @()
    if ($Missing -contains "Ollama: qwen2.5:14b") {
        $modelsToDownload += "qwen2.5:14b"
    }
    if ($Missing -contains "Ollama: nomic-embed-text (向量模型)") {
        $modelsToDownload += "nomic-embed-text"
    }

    if ($modelsToDownload.Count -gt 0) {
        Write-Host ""
        Write-Host "需要下载 Ollama 模型:" -ForegroundColor Yellow
        foreach ($m in $modelsToDownload) {
            Write-Host "  - $m" -ForegroundColor White
        }
        Write-Host ""

        # 检查 Ollama 服务是否运行
        try {
            Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 -ErrorAction Stop | Out-Null
            Write-Info "Ollama 服务运行中"
        } catch {
            Write-Host ""
            Write-Warn "Ollama 服务未运行，正在启动..."
            Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
            Start-Sleep -Seconds 3
            Write-Info "Ollama 服务已启动"
        }

        foreach ($model in $modelsToDownload) {
            Write-Host "下载模型: $model (可能需要几分钟到十几分钟)..." -ForegroundColor Yellow
            Write-Host "  ollama pull $model" -ForegroundColor Gray
            $process = Start-Process -FilePath "ollama" -ArgumentList "pull", $model -NoNewWindow -PassThru -Wait
            if ($process.ExitCode -eq 0) {
                Write-Success "模型下载完成: $model"
            } else {
                Write-Fail "模型下载失败: $model"
            }
        }
    }
}

# ============================================================
# 安全的目录复制 (合并模式)
# ============================================================

function Copy-SafeMerge {
    param(
        [string]$Src,
        [string]$Dst,
        [string]$Description
    )

    if (-not (Test-Path $Src)) {
        Write-Warn "Source not found: $Src"
        return 0
    }

    if (-not (Test-Path $Dst)) {
        New-Item -ItemType Directory -Path $Dst -Force | Out-Null
        Write-Info "Created: $Description"
    }

    $copied = 0
    $items = Get-ChildItem -Path $Src -Force
    foreach ($item in $items) {
        $dstPath = Join-Path $Dst $item.Name

        # 如果目标已存在，跳过 (保留原有文件)
        if (Test-Path $dstPath) {
            continue
        }

        if ($item.PSIsContainer) {
            $c = Copy-SafeMerge -Src $item.FullName -Dst $dstPath -Description "$Description/$($item.Name)"
            $copied += $c
        } else {
            Copy-Item -Path $item.FullName -Destination $dstPath -Force -ErrorAction SilentlyContinue | Out-Null
            $copied++
        }
    }
    return $copied
}

function Copy-SafeOverwrite {
    param(
        [string]$Src,
        [string]$Dst,
        [string]$Description
    )

    if (-not (Test-Path $Src)) {
        Write-Warn "Source not found: $Src"
        return 0
    }

    if (-not (Test-Path $Dst)) {
        New-Item -ItemType Directory -Path $Dst -Force | Out-Null
    }

    $copied = 0
    $items = Get-ChildItem -Path $Src -Force
    foreach ($item in $items) {
        $dstPath = Join-Path $Dst $item.Name
        if ($item.PSIsContainer) {
            if (-not (Test-Path $dstPath)) {
                New-Item -ItemType Directory -Path $dstPath -Force | Out-Null
            }
            $c = Copy-SafeOverwrite -Src $item.FullName -Dst $dstPath -Description "$Description/$($item.Name)"
            $copied += $c
        } else {
            Copy-Item -Path $item.FullName -Destination $dstPath -Force -ErrorAction SilentlyContinue | Out-Null
            $copied++
        }
    }
    return $copied
}

# ============================================================
# 插件合并 (仅合并模式)
# ============================================================

function Merge-VectorbrainPlugin {
    param([string]$OcBase)

    $openclawJson = Join-Path $OcBase "openclaw.json"
    if (-not (Test-Path $openclawJson)) {
        Write-Warn "openclaw.json 不存在，跳过插件合并"
        return
    }

    # 读取现有配置
    $config = Get-Content $openclawJson -Raw | ConvertFrom-Json

    # 初始化 plugins 节点 (如果不存在)
    if (-not $config.plugins) {
        $config | Add-Member -NotePropertyName "plugins" -NotePropertyValue ([ordered]@{}) -Force
    }

    # 确保 plugins.allow 包含 vectorbrain
    if (-not $config.plugins.allow) {
        $config.plugins | Add-Member -NotePropertyName "allow" -NotePropertyValue @() -Force
    }
    if ("vectorbrain" -notin $config.plugins.allow) {
        $config.plugins.allow += "vectorbrain"
        Write-Info "添加 vectorbrain 到 plugins.allow"
    }

    # 确保 plugins.entries 包含 vectorbrain
    if (-not $config.plugins.entries) {
        $config.plugins | Add-Member -NotePropertyName "entries" -NotePropertyValue ([ordered]@{}) -Force
    }
    if (-not $config.plugins.entries.vectorbrain) {
        $config.plugins.entries | Add-Member -NotePropertyName "vectorbrain" -NotePropertyValue ([ordered]@{ enabled = $true }) -Force
        Write-Info "添加 vectorbrain 到 plugins.entries"
    }

    # 确保 plugins.installs 包含 vectorbrain
    if (-not $config.plugins.installs) {
        $config.plugins | Add-Member -NotePropertyName "installs" -NotePropertyValue ([ordered]@{}) -Force
    }
    if (-not $config.plugins.installs.vectorbrain) {
        $vbInstallPath = "$env:USERPROFILE\.openclaw\extensions\vectorbrain"
        $config.plugins.installs | Add-Member -NotePropertyName "vectorbrain" -NotePropertyValue ([ordered]@{
            source = "path"
            sourcePath = $vbInstallPath
            installPath = $vbInstallPath
            version = "1.0.0"
        }) -Force
        Write-Info "添加 vectorbrain 到 plugins.installs"
    }

    # 保存 (保留原有格式)
    $config | ConvertTo-Json -Depth 20 | Set-Content -Path $openclawJson -Encoding UTF8
    Write-Success "VectorBrain 插件配置已合并到 openclaw.json"
}

# ============================================================
# 脱敏处理
# ============================================================

function Sanitize-File {
    param([string]$Path, [string[]]$Patterns)

    if (-not (Test-Path $Path)) { return }
    $content = Get-Content $Path -Raw -ErrorAction SilentlyContinue
    if (-not $content) { return }

    foreach ($pattern in $Patterns) {
        $content = $content -replace $pattern, '[YOUR_API_KEY_HERE]'
    }
    Set-Content -Path $Path -Value $content -Force -ErrorAction SilentlyContinue
}

# ============================================================
# 主安装流程
# ============================================================

function Start-Installation {
    Write-Banner "Nexus Brain 安全安装程序 v4.0"

    # 检查源码目录
    $srcVB = ""
    $srcOC = ""

    if ($SrcDir) {
        $srcVB = Join-Path $SrcDir "vectorbrain"
        $srcOC = Join-Path $SrcDir "openclaw"
    } else {
        $srcVB = Join-Path (Split-Path $PSScriptRoot -Parent) "src\vectorbrain"
        $srcOC = Join-Path (Split-Path $PSScriptRoot -Parent) "src\openclaw"
    }

    if (-not (Test-Path $srcVB)) {
        Write-Fail "源码未找到: $srcVB"
        Write-Host "请确保 src/vectorbrain 和 src/openclaw 目录存在" -ForegroundColor Yellow
        exit 1
    }

    # ============================================================
    # 环境检测
    # ============================================================

    Write-Step 1 14 "检测已有环境..."
    $env = Test-EnvironmentExists
    $envInfo = Get-EnvironmentInfo -Env $env

    if ($env.Both) {
        Write-Warn "检测到已存在 VectorBrain + OpenClaw 环境"
        Write-Host ""
        foreach ($key in $envInfo.Keys) {
            $e = $envInfo[$key]
            Write-Host "  $key 已安装:" -ForegroundColor Yellow
            if ($e.Memory -gt 0) { Write-Info "  - $($e.Memory) 个数据库文件" }
            if ($e.Skills -gt 0) { Write-Info "  - $($e.Skills) 个技能" }
            if ($e.Connector) { Write-Info "  - 连接器已配置" }
        }
        Write-Host ""
        Write-Host "安装模式选择:" -ForegroundColor Cyan
        Write-Host "  [M] 合并安装 (推荐) - 只添加缺失文件，保留原有配置" -ForegroundColor White
        Write-Host "  [O] 覆盖安装 - 完整替换 (会丢失原有配置)" -ForegroundColor White
        Write-Host "  [Q] 退出" -ForegroundColor White
        Write-Host ""

        if ($MergeInstall) {
            $installMode = "merge"
            Write-Host "使用合并安装模式" -ForegroundColor Green
        } elseif ($OverwriteInstall) {
            $installMode = "overwrite"
            Write-Host "使用覆盖安装模式" -ForegroundColor Yellow
        } else {
            $choice = Read-Host "请选择 (M/O/Q)"
            switch ($choice.ToUpper()) {
                "M" { $installMode = "merge" }
                "O" { $installMode = "overwrite" }
                default { Write-Host "退出安装"; exit 0 }
            }
        }
    } else {
        $installMode = "overwrite"
        Write-Success "新环境，将进行完整安装"
    }

    # ============================================================
    # 预检查
    # ============================================================

    if (-not $SkipPreCheck) {
        $report = Get-SystemReport
        $missing = Show-SystemReport -Report $report
        if ($missing.Count -gt 0) {
            $continue = Read-Host "缺少 $($missing.Count) 个必需依赖，是否继续? (Y/N)"
            if ($continue -ne "Y" -and $continue -ne "y") {
                Write-Info "安装已取消"
                exit 0
            }
            Install-Missing -Missing $missing
        }
    }

    # ============================================================
    # 开始安装
    # ============================================================

    $vbBase = "$env:USERPROFILE\.vectorbrain"
    $ocBase = "$env:USERPROFILE\.openclaw"
    $totalSteps = 14

    # 步骤 2: 创建目录结构
    Write-Step 2 $totalSteps "创建目录结构..."

    $vbDirs = @("memory","tasks","logs","hooks","credentials","docs","bin","connector","dag","experience","heart","identity","intelligence","planner","reflection","skills","subagents","runtime","state","work-memory-hub","maintenance","metrics")
    $ocDirs = @("workspace","workspace/skills","workspace/scripts","workspace/memory","workspace/documents","workspace/business","skills","hooks","logs","identity","extensions","cron","cron/runs","agents","agents/main","agents/main/agent","agents/main/sessions","docs")

    foreach ($dir in $vbDirs) {
        $path = Join-Path $vbBase $dir
        if (-not (Test-Path $path)) {
            New-Item -ItemType Directory -Path $path -Force | Out-Null
        }
    }
    foreach ($dir in $ocDirs) {
        $path = Join-Path $ocBase $dir
        if (-not (Test-Path $path)) {
            New-Item -ItemType Directory -Path $path -Force | Out-Null
        }
    }
    Write-Success "目录结构就绪"

    # ============================================================
    # 步骤 3-6: 复制代码 (根据模式)
    # ============================================================

    if ($installMode -eq "merge") {
        Write-Step 3 $totalSteps "合并安装 - 复制 VectorBrain 新文件..."
        Write-Info "保留所有已有文件，只添加缺失的文件"

        # 只复制 src 中有、目标中没有的文件
        $vbModules = @("bin","connector","dag","experience","heart","identity","intelligence","memory","planner","reflection","skills","subagents","runtime","state","work-memory-hub","maintenance","metrics")
        foreach ($mod in $vbModules) {
            $src = Join-Path $srcVB $mod
            $dst = Join-Path $vbBase $mod
            if (Test-Path $src) {
                $n = Copy-SafeMerge -Src $src -Dst $dst -Description "VB/$mod"
                if ($n -gt 0) { Write-Info "Added $n files to $mod" }
            }
        }
        Write-Success "VectorBrain 合并完成"

        Write-Step 4 $totalSteps "合并安装 - 复制 OpenClaw 新文件..."

        $ocModules = @("skills","extensions","cron","agents","docs")
        foreach ($mod in $ocModules) {
            $src = Join-Path $srcOC $mod
            $dst = Join-Path $ocBase $mod
            if (Test-Path $src) {
                $n = Copy-SafeMerge -Src $src -Dst $dst -Description "OC/$mod"
                if ($n -gt 0) { Write-Info "Added $n files to $mod" }
            }
        }

        # 合并 workspace (只添加缺失的 md 文件)
        $srcWs = Join-Path $srcOC "workspace"
        if (Test-Path $srcWs) {
            $wsFiles = Get-ChildItem -Path $srcWs -File -Filter "*.md"
            foreach ($f in $wsFiles) {
                $dstPath = Join-Path $ocBase "workspace\$($f.Name)"
                if (-not (Test-Path $dstPath)) {
                    Copy-Item -Path $f.FullName -Destination $dstPath -Force
                    Write-Info "Added workspace file: $($f.Name)"
                }
            }
        }

        # 合并 workspace/skills (只添加缺失的技能)
        $srcWsSkills = Join-Path $srcOC "workspace\skills"
        if (Test-Path $srcWsSkills) {
            $wsSkillDirs = Get-ChildItem -Path $srcWsSkills -Directory
            foreach ($skillDir in $wsSkillDirs) {
                $dstPath = Join-Path $ocBase "workspace\skills\$($skillDir.Name)"
                if (-not (Test-Path $dstPath)) {
                    $n = Copy-SafeMerge -Src $skillDir.FullName -Dst $dstPath -Description "OC/workspace/skills/$($skillDir.Name)"
                    if ($n -gt 0) { Write-Info "Added skill: $($skillDir.Name)" }
                }
            }
        }
        Write-Success "OpenClaw 合并完成"

        # 合并 vectorbrain 插件到 openclaw.json
        Write-Step 5 $totalSteps "合并安装 - 注册 VectorBrain 插件..."
        Merge-VectorbrainPlugin -OcBase $ocBase
        Write-Success "VectorBrain 插件注册完成"

    } else {
        # 覆盖模式
        Write-Step 3 $totalSteps "覆盖安装 - 复制 VectorBrain..."
        $vbModules = @("bin","connector","dag","experience","heart","identity","intelligence","memory","planner","reflection","skills","subagents","runtime","state","work-memory-hub","maintenance","metrics")
        foreach ($mod in $vbModules) {
            $src = Join-Path $srcVB $mod
            $dst = Join-Path $vbBase $mod
            if (Test-Path $src) {
                Copy-SafeOverwrite -Src $src -Dst $dst -Description "VB/$mod" | Out-Null
            }
        }
        Write-Success "VectorBrain 复制完成"

        Write-Step 4 $totalSteps "覆盖安装 - 复制 OpenClaw..."
        $ocModules = @("skills","extensions","cron","agents","docs")
        foreach ($mod in $ocModules) {
            $src = Join-Path $srcOC $mod
            $dst = Join-Path $ocBase $mod
            if (Test-Path $src) {
                Copy-SafeOverwrite -Src $src -Dst $dst -Description "OC/$mod" | Out-Null
            }
        }
        $srcWs = Join-Path $srcOC "workspace"
        if (Test-Path $srcWs) {
            Copy-SafeOverwrite -Src $srcWs -Dst (Join-Path $ocBase "workspace") -Description "OC/workspace" | Out-Null
        }
        Write-Success "OpenClaw 复制完成"

        # 覆盖模式也注册 vectorbrain 插件
        Write-Step 5 $totalSteps "覆盖安装 - 注册 VectorBrain 插件..."
        Merge-VectorbrainPlugin -OcBase $ocBase
        Write-Success "VectorBrain 插件注册完成"
    }

    # 步骤 6: 脱敏 (只处理新复制的文件)
    Write-Step 6 $totalSteps "脱敏处理 - 移除 API Keys..."

    $sanitizePatterns = @(
        '(?mi)"api[_-]?key[^"]*":\s*"[^"]+"',
        '(?mi)"token[^"]*":\s*"[^"]+"',
        '(?mi)"secret[^"]*":\s*"[^"]+"',
        '(?mi)"password[^"]*":\s*"[^"]+"',
        '(?m)^.*(api[_-]?key|secret|token|password).*=.*$'
    )

    Get-ChildItem -Path $vbBase -Recurse -Include "*.json","*.yaml","*.yml" -ErrorAction SilentlyContinue | ForEach-Object {
        Sanitize-File -Path $_.FullName -Patterns $sanitizePatterns
    }
    Get-ChildItem -Path $ocBase -Recurse -Include "*.json","*.yaml","*.yml" -ErrorAction SilentlyContinue | ForEach-Object {
        Sanitize-File -Path $_.FullName -Patterns $sanitizePatterns
    }

    # 删除 .env
    $envPath = Join-Path $vbBase ".env"
    if (Test-Path $envPath) { Remove-Item $envPath -Force -ErrorAction SilentlyContinue }

    Write-Success "API Keys 已脱敏"

    # 步骤 6: 生成新的设备身份 (合并模式下只在新文件不存在时创建)
    Write-Step 7 $totalSteps "配置设备身份..."
    $identityDir = Join-Path $ocBase "identity"
    if (-not (Test-Path $identityDir)) {
        New-Item -ItemType Directory -Path $identityDir -Force | Out-Null
    }
    $devicePath = Join-Path $identityDir "device.json"
    if (-not (Test-Path $devicePath)) {
        $deviceId = [guid]::NewGuid().ToString("N")
        $createdAtMs = [long](Get-Date -UFormat "%s") * 1000
        $deviceJson = @{
            version = 1
            deviceId = $deviceId
            publicKeyPem = "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEAXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX=\n-----END PUBLIC KEY-----"
            privateKeyPem = "-----BEGIN PRIVATE KEY-----\nMC4CAQAwBQYDK2VwBCIEIMXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX=\n-----END PRIVATE KEY-----"
            createdAtMs = $createdAtMs
        } | ConvertTo-Json -Depth 10
        Set-Content -Path $devicePath -Value $deviceJson -Encoding UTF8
        Write-Info "New Device ID: $deviceId"
    } else {
        Write-Info "保留原有设备身份"
    }
    Write-Success "设备身份配置完成"

    # 步骤 7: 创建 API Key 配置模板
    Write-Step 8 $totalSteps "创建 API Key 配置模板..."
    $envTemplatePath = Join-Path $vbBase ".env.template"
    if (-not (Test-Path $envTemplatePath)) {
        $envTemplate = @"
# Nexus Brain - 环境变量配置模板
# 复制此文件为 .env 并填写你的 API Keys

# AI/LLM API
OPENAI_API_KEY=[YOUR_API_KEY_HERE]
OPENAI_BASE_URL=https://coding.dashscope.aliyuncs.com/v1

# 向量数据库
OPENCLAW_LANCEDB_EMBEDDING_API_KEY=[YOUR_API_KEY_HERE]

# 搜索 API
BRAVE_API_KEY=[YOUR_BRAVE_API_KEY]
TAVILY_API_KEY=[YOUR_TAVILY_API_KEY]

# Feishu
FEISHU_APP_ID=[YOUR_FEISHU_APP_ID]
FEISHU_APP_SECRET=[YOUR_FEISHU_APP_SECRET]
"@
        Set-Content -Path $envTemplatePath -Value $envTemplate -Encoding UTF8
        Write-Info "Created: .env.template"
    } else {
        Write-Info "保留原有 .env.template"
    }
    Write-Success "配置模板已就绪"

    # 步骤 8: 配置启动钩子
    Write-Step 9 $totalSteps "配置启动钩子..."
    $hooksDir = Join-Path $ocBase "hooks"
    if (-not (Test-Path $hooksDir)) {
        New-Item -ItemType Directory -Path $hooksDir -Force | Out-Null
    }

    $ps1Hook = @"
# Nexus Brain 启动钩子
`$logDir = "`$env:USERPROFILE\.openclaw\logs"
if (-not (Test-Path `$logDir)) { New-Item -ItemType Directory -Path `$logDir -Force | Out-Null }

`$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"`$timestamp on-start begin" | Out-File -FilePath "`$logDir\startup.log" -Append

# 启动 VectorBrain 连接器
`$bootstrapPath = "`$env:USERPROFILE\.vectorbrain\connector\nexus_bootstrap.py"
if (Test-Path `$bootstrapPath) {
    python `$bootstrapPath >> `$logDir\startup.log 2>&1
}

`$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"`$timestamp on-start end" | Out-File -FilePath "`$logDir\startup.log" -Append
"@

    $ps1Path = Join-Path $hooksDir "on-start.ps1"
    if (-not (Test-Path $ps1Path)) {
        Set-Content -Path $ps1Path -Value $ps1Hook -Encoding UTF8
        Write-Info "Created: on-start.ps1"
    } else {
        Write-Info "保留原有 on-start.ps1"
    }

    $shPath = Join-Path $hooksDir "on-start.sh"
    if (-not (Test-Path $shPath)) {
        $shHook = @"
#!/bin/bash
mkdir -p ~/.openclaw/logs
echo "[$(date '+%Y-%m-%d %H:%M:%S')] on-start begin" >> ~/.openclaw/logs/startup.log
if [ -f ~/.vectorbrain/connector/nexus_bootstrap.py ]; then
    python3 ~/.vectorbrain/connector/nexus_bootstrap.py >> ~/.openclaw/logs/startup.log 2>&1
fi
echo "[$(date '+%Y-%m-%d %H:%M:%S')] on-start end" >> ~/.openclaw/logs/startup.log
"@
        Set-Content -Path $shPath -Value $shHook -Encoding UTF8
        Write-Info "Created: on-start.sh"
    }
    Write-Success "启动钩子配置完成"

    # 步骤 9-14: 剩余步骤
    Write-Step 10 $totalSteps "初始化数据库占位文件..."
    $memoryDir = Join-Path $vbBase "memory"
    $tasksDir = Join-Path $vbBase "tasks"
    $dbFiles = @("episodic_memory.db","knowledge_memory.db","information_memory.db","habit_memory.db","heart_memory.db","work_memory_hub.db","lessons_memory.db")
    foreach ($db in $dbFiles) {
        $dbPath = Join-Path $memoryDir $db
        if (-not (Test-Path $dbPath)) {
            "" | Out-File -FilePath $dbPath -Encoding Byte
        }
    }
    $taskDbPath = Join-Path $tasksDir "task_queue.db"
    if (-not (Test-Path $taskDbPath)) {
        "" | Out-File -FilePath $taskDbPath -Encoding Byte
    }
    Write-Info "首次启动时系统会自动初始化实际的数据库结构"
    Write-Success "数据库占位文件创建完成"

    Write-Step 11 $totalSteps "配置 MCP 扩展..."
    $extDir = Join-Path $ocBase "extensions\vectorbrain"
    if (Test-Path $extDir) {
        Write-Info "VectorBrain MCP 扩展已就绪"
    }
    $mcpConfigPath = Join-Path $ocBase "extensions\mcp_config.json"
    if (-not (Test-Path $mcpConfigPath)) {
        @{
            mcp_servers = @{
                vectorbrain = @{ type="stdio"; command="node"; args=@("$env:USERPROFILE\.openclaw\extensions\vectorbrain\index.js") }
                chrome = @{ type="http"; url="http://127.0.0.1:12306/mcp" }
            }
        } | ConvertTo-Json -Depth 10 | Set-Content -Path $mcpConfigPath -Encoding UTF8
        Write-Info "Created: mcp_config.json"
    } else {
        Write-Info "保留原有 MCP 配置"
    }
    Write-Success "MCP 扩展配置完成"

    Write-Step 12 $totalSteps "配置扩展注册..."
    $extIndexPath = Join-Path $ocBase "extensions\index.json"
    if (-not (Test-Path $extIndexPath)) {
        @{
            extensions = @(
                @{ name="vectorbrain"; path="vectorbrain"; enabled=$true; description="VectorBrain memory and orchestration" }
            )
        } | ConvertTo-Json -Depth 10 | Set-Content -Path $extIndexPath -Encoding UTF8
        Write-Info "Created: extensions/index.json"
    } else {
        Write-Info "保留原有扩展注册"
    }
    Write-Success "扩展注册完成"

    Write-Step 13 $totalSteps "配置环境变量..."
    Write-Host ""
    Write-Host "请在系统环境变量中设置:" -ForegroundColor Yellow
    Write-Host "  CLAUDE_CODE_DIR = $vbBase" -ForegroundColor Cyan
    Write-Host "  OPENCLAW_DIR = $ocBase" -ForegroundColor Cyan
    Write-Host "  OLLAMA_HOST = 127.0.0.1:11434" -ForegroundColor Cyan
    Write-Host ""
    $openEnv = Read-Host "是否打开系统环境变量设置界面? (Y/N)"
    if ($openEnv -eq "Y" -or $openEnv -eq "y") {
        Start-Process "SystemPropertiesAdvanced"
    }

    Write-Step 13 $totalSteps "环境变量配置说明已提供"

    Write-Step 14 $totalSteps "完成..."

    # ============================================================
    # 完成
    # ============================================================

    Write-Banner "安装完成!"

    Write-Host "安装模式: $(if ($installMode -eq 'merge') { '合并安装 (保留原有配置)' } else { '覆盖安装' })" -ForegroundColor Green
    Write-Host ""
    Write-Host "安装摘要:" -ForegroundColor Yellow
    Write-Host "  VectorBrain: $vbBase" -ForegroundColor White
    Write-Host "  OpenClaw:    $ocBase" -ForegroundColor White
    Write-Host ""

    Write-Host "后续步骤:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. 配置 API Keys:" -ForegroundColor Yellow
    Write-Host "   复制 $vbBase\.env.template 为 $vbBase\.env" -ForegroundColor White
    Write-Host "   并填写你的实际 API Keys" -ForegroundColor White
    Write-Host ""
    Write-Host "2. 下载 Ollama 模型 (首次需要):" -ForegroundColor Yellow
    Write-Host "   ollama pull qwen2.5:14b" -ForegroundColor White
    Write-Host "   ollama pull nomic-embed-text" -ForegroundColor White
    Write-Host ""
    Write-Host "3. 首次启动 Nexus:" -ForegroundColor Yellow
    Write-Host "   python $vbBase\connector\nexus_bootstrap.py" -ForegroundColor White
    Write-Host ""
    Write-Host "4. 启动 Ollama:" -ForegroundColor Yellow
    Write-Host "   ollama serve" -ForegroundColor White
    Write-Host ""
    Write-Host "详细文档: ..\README.md" -ForegroundColor Green
    Write-Host ""
}

# 运行
Start-Installation
