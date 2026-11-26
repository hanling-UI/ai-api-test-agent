# 本地一键启动：被测服务(9000) + 应用(8000)，并打开浏览器
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$env:DATABASE_URL = 'postgresql+psycopg://postgres:postgres@127.0.0.1:5433/postgres'
$env:TARGET_BASE_URL = 'http://127.0.0.1:9000'
$key = [Environment]::GetEnvironmentVariable('OPENAI_API_KEY', 'User')
if ($key) { $env:OPENAI_API_KEY = $key } else { Write-Host '警告：未找到用户级 OPENAI_API_KEY，生成用例会失败' -ForegroundColor Yellow }

# 确保数据库容器在跑
$running = docker ps --filter name=pgv --format '{{.Names}}'
if (-not $running) {
    Write-Host '启动 pgv 容器…'
    docker start pgv | Out-Null
    Start-Sleep -Seconds 5
}

Write-Host '启动被测服务 :9000'
Start-Process python -ArgumentList '-m','uvicorn','mock_server.main:app','--port','9000' -WindowStyle Hidden
Start-Sleep -Seconds 4

Write-Host '启动应用 :8000'
Start-Process python -ArgumentList '-m','uvicorn','main:app','--port','8000' -WindowStyle Hidden
Start-Sleep -Seconds 5

Write-Host '打开浏览器 http://127.0.0.1:8000' -ForegroundColor Green
Start-Process 'http://127.0.0.1:8000'
