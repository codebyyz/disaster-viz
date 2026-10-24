# 检查 Docker Desktop 安装位置 / 服务 / WSL 集成状态
Write-Output "== 安装位置 =="
foreach ($p in 'D:\Docker', 'C:\Program Files\Docker') {
    if (Test-Path $p) {
        $mb = (Get-ChildItem $p -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum / 1MB
        Write-Output ("{0}  {1:N1} MB" -f $p, $mb)
    } else {
        Write-Output ("{0}  (不存在)" -f $p)
    }
}

Write-Output "== 服务 =="
Get-Service -Name 'com.docker.service' -ErrorAction SilentlyContinue | Select-Object Name, Status | Format-Table -AutoSize

Write-Output "== 进程 =="
Get-Process | Where-Object { $_.ProcessName -match 'docker' } | Select-Object Id, ProcessName | Format-Table -AutoSize

Write-Output "== 磁盘 =="
Get-PSDrive C, D | Select-Object Name,
    @{n='UsedGB'; e={[math]::Round($_.Used/1GB,1)}},
    @{n='FreeGB'; e={[math]::Round($_.Free/1GB,1)}} | Format-Table -AutoSize
