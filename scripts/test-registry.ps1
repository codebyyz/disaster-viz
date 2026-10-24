# 测试 Docker Hub 及其国内镜像站的可达性
# Docker Desktop 拉镜像不走 Windows 的系统代理设置，所以这里只测网络连通性，
# 真正的加速要写进 Settings -> Docker Engine 的 registry-mirrors。
$ErrorActionPreference = 'SilentlyContinue'

$targets = @(
    @{ name = 'Docker Hub 官方';        url = 'https://registry-1.docker.io/v2/' },
    @{ name = 'DaoCloud 镜像';          url = 'https://docker.m.daocloud.io/v2/' },
    @{ name = 'dockerproxy.net';        url = 'https://dockerproxy.net/v2/' },
    @{ name = '1ms.run';                url = 'https://docker.1ms.run/v2/' },
    @{ name = '阿里云(需个人地址)';      url = 'https://registry.cn-hangzhou.aliyuncs.com/v2/' }
)

foreach ($t in $targets) {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $r = Invoke-WebRequest -Uri $t.url -TimeoutSec 8 -UseBasicParsing -ErrorAction Stop
        $sw.Stop()
        Write-Output ("{0,-24} HTTP {1}  {2:N2}s" -f $t.name, $r.StatusCode, $sw.Elapsed.TotalSeconds)
    } catch {
        $sw.Stop()
        $msg = $_.Exception.Message
        if ($msg.Length -gt 60) { $msg = $msg.Substring(0, 60) }
        Write-Output ("{0,-24} FAIL  {1:N2}s  {2}" -f $t.name, $sw.Elapsed.TotalSeconds, $msg)
    }
}
