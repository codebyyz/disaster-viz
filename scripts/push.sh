#!/usr/bin/env bash
# WSL 里 push 到 GitHub 的排查 / 重试脚本
#
# 背景（2026-10-24 实测）：
#   代理 9674 端口在 Windows 侧已不再监听，WSL 的 git 仍指向它会 "Proxy CONNECT aborted"；
#   而 github.com / api.github.com 在这个网络下**直连可用**（200）。
#   所以本脚本走「临时关闭代理 -> push -> 恢复原有代理配置」的路子，
#   不改动 ~/.gitconfig 的长期设置。
set -uo pipefail
cd "$HOME/disaster-viz" || exit 1

HTTP_P=$(git config --global --get http.proxy || true)
HTTPS_P=$(git config --global --get https.proxy || true)

restore() {
  [ -n "${HTTP_P:-}" ] && git config --global http.proxy "$HTTP_P"
  [ -n "${HTTPS_P:-}" ] && git config --global https.proxy "$HTTPS_P"
}

echo "== 探测直连 github.com =="
code=$(curl -s -o /dev/null -m 20 -w '%{http_code}' https://github.com || echo 000)
echo "   HTTP $code"

if [ "$code" = "200" ]; then
  echo "== 直连可用，临时关闭代理后 push =="
  git config --global --unset-all http.proxy || true
  git config --global --unset-all https.proxy || true
  timeout 120 git push origin main
  rc=$?
  restore
  echo "push rc=$rc（原代理配置已恢复：${HTTPS_P:-none}）"
else
  echo "== 直连不通，保留代理配置重试 =="
  timeout 120 git push origin main || echo "仍失败：检查代理端口是否在监听（PowerShell: netstat -ano | findstr 9674）"
fi

git status -sb | head -3
