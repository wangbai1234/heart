# scripts/start-windows.ps1 — Windows 本地完整项目启动脚本
#
# 适用场景：Windows 测试机（Docker Desktop + PowerShell 5.1 / 7+）
# 启动内容：
#   1. postgres + redis (Docker Desktop)
#   2. 后端 API + 全部 workers (uvicorn, HEART_WORKERS_ENABLED=true)
#   3. 前端开发服务器 (Vite)
#
# 用法（PowerShell 以管理员或普通用户运行均可）：
#   .\scripts\start-windows.ps1                完整启动（首次 or 重启）
#   .\scripts\start-windows.ps1 -Stop          停止所有服务
#   .\scripts\start-windows.ps1 -BackendOnly   仅启动后端（跳过前端）
#   .\scripts\start-windows.ps1 -Migrate       仅跑 DB 迁移
#
# 前置条件：
#   - Docker Desktop 已安装并运行（Windows 10/11）
#   - Python 3.11+ 已安装（backend venv 或全局均可）
#   - Node.js 18+ 已安装（前端构建）
#   - backend/.env 文件已创建（从 .env.example 复制并填写）
#   - 首次运行前：cd backend && pip install -r requirements.txt

param(
    [switch]$Stop,
    [switch]$BackendOnly,
    [switch]$Migrate
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$BackendDir = Join-Path $RepoRoot "backend"
$WebDir = Join-Path $RepoRoot "web"
$EnvFile = Join-Path $BackendDir ".env"
$ComposeFile = Join-Path $RepoRoot "docker-compose.yml"

function Write-Green([string]$msg)  { Write-Host "[start] $msg" -ForegroundColor Green }
function Write-Blue([string]$msg)   { Write-Host "[info]  $msg" -ForegroundColor Cyan }
function Write-Yellow([string]$msg) { Write-Host "[warn]  $msg" -ForegroundColor Yellow }
function Write-Red([string]$msg)    { Write-Host "[error] $msg" -ForegroundColor Red }

# ──────────────────────────────────────────────────────────────────────────────
# -Stop: 停止所有进程
# ──────────────────────────────────────────────────────────────────────────────
if ($Stop) {
    Write-Green "停止所有 Heart 服务..."

    # 停 docker compose (postgres + redis)
    if (Test-Path $ComposeFile) {
        Write-Blue "停止 Docker 容器..."
        docker compose -f $ComposeFile down 2>$null
    }

    # 停 uvicorn 进程
    $uvicorn = Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue
    if ($uvicorn) {
        $uvicorn | Stop-Process -Force
        Write-Blue "uvicorn 已停止"
    }

    # 停 python 进程（按命令行关键词过滤）
    Get-Process -Name "python*" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*heart*" -or $_.CommandLine -like "*uvicorn*"
    } | Stop-Process -Force -ErrorAction SilentlyContinue

    # 停 vite / node 进程
    Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*vite*" -or $_.CommandLine -like "*heart*"
    } | Stop-Process -Force -ErrorAction SilentlyContinue

    Write-Green "✅ 已停止所有服务"
    exit 0
}

# ──────────────────────────────────────────────────────────────────────────────
# 前置检查
# ──────────────────────────────────────────────────────────────────────────────
function Test-Command([string]$cmd) {
    $null = Get-Command $cmd -ErrorAction SilentlyContinue
    return $?
}

Write-Green "Heart/yuoyuo — Windows 启动脚本"
Write-Host "──────────────────────────────────────────────"

if (-not (Test-Command "docker")) {
    Write-Red "docker 未找到。请安装 Docker Desktop: https://www.docker.com/products/docker-desktop/"
    exit 1
}

try {
    docker ps 2>&1 | Out-Null
} catch {
    Write-Red "Docker Desktop 未运行，请启动后再试。"
    exit 1
}

if (-not (Test-Path $EnvFile)) {
    Write-Red ".env 文件不存在: $EnvFile"
    Write-Yellow "请先执行: Copy-Item backend\.env.example backend\.env  然后填写 API 密钥"
    exit 1
}

if (-not (Test-Command "python")) {
    Write-Red "Python 未找到，请安装 Python 3.11+"
    exit 1
}

# ──────────────────────────────────────────────────────────────────────────────
# 1. 启动 postgres + redis
# ──────────────────────────────────────────────────────────────────────────────
Write-Green "启动 postgres + redis..."
docker compose -f $ComposeFile up -d postgres redis

# 等待 postgres 就绪
Write-Blue "等待 postgres 就绪..."
$ready = $false
for ($i = 1; $i -le 30; $i++) {
    $result = docker compose -f $ComposeFile ps postgres 2>&1
    if ($result -match "healthy") {
        Write-Blue "✓ postgres 就绪 (${i}s)"
        $ready = $true
        break
    }
    Start-Sleep -Seconds 1
}
if (-not $ready) {
    Write-Red "postgres 30s 内未就绪，查看日志: docker compose logs postgres"
    exit 1
}

# ──────────────────────────────────────────────────────────────────────────────
# -Migrate: 仅跑迁移
# ──────────────────────────────────────────────────────────────────────────────
if ($Migrate) {
    Write-Green "运行 Alembic 迁移..."
    Push-Location $BackendDir
    try {
        $env:PYTHONPATH = $BackendDir
        python -m alembic upgrade 022_identity_narrative_backfill
        python -m alembic upgrade 033_chat_messages_is_proactive
        python -m alembic current
        Write-Green "✅ 迁移完成"
    } finally {
        Pop-Location
    }
    exit 0
}

# ──────────────────────────────────────────────────────────────────────────────
# 2. 读取 .env，提取 DATABASE_URL 与 REDIS_URL 供本地进程使用
#    （docker-compose.yml 里的 postgres/redis 监听 localhost:5432/6379）
# ──────────────────────────────────────────────────────────────────────────────
Write-Blue "加载 .env 环境变量..."
Get-Content $EnvFile | Where-Object { $_ -match "^[A-Z]" -and $_ -notmatch "^#" } | ForEach-Object {
    $parts = $_ -split "=", 2
    if ($parts.Count -eq 2) {
        $key = $parts[0].Trim()
        $value = $parts[1].Trim()
        [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# 3. 运行 DB 迁移（首次 or 代码更新后）
# ──────────────────────────────────────────────────────────────────────────────
Write-Green "运行 Alembic 迁移..."
Push-Location $BackendDir
try {
    python -m alembic upgrade 022_identity_narrative_backfill
    python -m alembic upgrade 033_chat_messages_is_proactive
} catch {
    Write-Yellow "迁移警告（如果 schema 已最新可忽略）: $_"
} finally {
    Pop-Location
}

# ──────────────────────────────────────────────────────────────────────────────
# 4. 启动后端 uvicorn（带全部 workers）
#    新开 PowerShell 窗口，保持日志可见
# ──────────────────────────────────────────────────────────────────────────────
Write-Green "启动后端 API + Workers..."
$backendCmd = "cd '$BackendDir'; `$env:HEART_WORKERS_ENABLED='true'; python -m uvicorn heart.api.main:app --host 0.0.0.0 --port 8000 --reload; pause"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd -WindowStyle Normal

# 等待后端健康
Write-Blue "等待后端就绪..."
$apiReady = $false
for ($i = 1; $i -le 60; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health/live" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Blue "✓ 后端就绪 (${i}s)"
            $apiReady = $true
            break
        }
    } catch {}
    Start-Sleep -Seconds 1
}
if (-not $apiReady) {
    Write-Yellow "后端 60s 内未响应，请检查后端窗口的错误信息。前端将继续启动..."
}

# ──────────────────────────────────────────────────────────────────────────────
# 5. 启动前端 Vite（-BackendOnly 时跳过）
# ──────────────────────────────────────────────────────────────────────────────
if (-not $BackendOnly) {
    if (-not (Test-Command "node")) {
        Write-Yellow "Node.js 未找到，跳过前端启动。安装 Node.js 18+: https://nodejs.org/"
    } elseif (-not (Test-Path $WebDir)) {
        Write-Yellow "web/ 目录不存在，跳过前端启动"
    } else {
        Write-Green "启动前端 Vite..."
        $frontendCmd = "cd '$WebDir'; npm run dev; pause"
        Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd -WindowStyle Normal
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# 完成
# ──────────────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Green "✅ Heart/yuoyuo 启动完成"
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Blue "服务地址："
Write-Host "  前端:          http://localhost:5173"
Write-Host "  后端 API:      http://localhost:8000"
Write-Host "  健康检查:      http://localhost:8000/health/live"
Write-Host "  API 文档:      http://localhost:8000/docs"
Write-Host ""
Write-Blue "Workers（在后端窗口中运行，HEART_WORKERS_ENABLED=true）："
Write-Host "  memory_encoder  memory_extractor  memory_promoter"
Write-Host "  inner_loop (proactive)  account_purge  credit_reconciliation"
Write-Host ""
Write-Blue "常用操作："
Write-Host "  停止所有:      .\scripts\start-windows.ps1 -Stop"
Write-Host "  仅后端:        .\scripts\start-windows.ps1 -BackendOnly"
Write-Host "  仅迁移:        .\scripts\start-windows.ps1 -Migrate"
Write-Host ""
Write-Yellow "提示：前端和后端分别在独立的 PowerShell 窗口中运行，关闭窗口即停止对应服务。"
Write-Yellow "      或运行 .\scripts\start-windows.ps1 -Stop 一键停止全部。"
