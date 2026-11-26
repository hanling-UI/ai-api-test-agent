# 一键释放 8000/9000 端口（启动服务前跑一次，避免 Errno 10048）
$freed = @()
foreach ($port in 8000, 9000) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        $proc = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
        Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
        $freed += "端口 $port ← $($proc.ProcessName) (pid $($c.OwningProcess))"
    }
}
if ($freed.Count -eq 0) {
    Write-Host '端口 8000/9000 都空闲，可以直接启动服务' -ForegroundColor Green
} else {
    $freed | ForEach-Object { Write-Host "已释放：$_" -ForegroundColor Yellow }
}
