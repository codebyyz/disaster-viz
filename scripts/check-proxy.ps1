# 检查本机代理端口（青山 / Clash Meta 内核）是否可用
Write-Output "== listening ports =="
foreach ($p in 9674,9675,9676,7890,10808) {
    $conn = Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue
    if ($conn) {
        $procId = ($conn | Select-Object -First 1).OwningProcess
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        Write-Output ("port {0}: LISTEN pid={1} name={2}" -f $p, $procId, $proc.ProcessName)
    } else {
        Write-Output ("port {0}: not listening" -f $p)
    }
}

Write-Output "== test http via proxy =="
foreach ($p in 9674,9675,9676) {
    try {
        $r = Invoke-WebRequest -Uri "https://github.com" -Proxy ("http://127.0.0.1:" + $p) -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
        Write-Output ("proxy {0}: HTTP {1}" -f $p, $r.StatusCode)
    } catch {
        Write-Output ("proxy {0}: FAIL {1}" -f $p, $_.Exception.Message)
    }
}
