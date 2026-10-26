# 两阶段构建：
#   1) builder —— 装依赖、编译前端静态资源（产物留在镜像中间层，不进最终镜像）
#   2) runtime —— 只放 venv + 构建产物，镜像更小、攻击面更小
#
# 为什么前端要在 Docker 里构建而不是把 dist/ 拷进来：
# 构建产物由源码保证一致，谁 clone 下来 docker compose up 都能得到同样的东西。
#
# 注意：基础镜像用了 Docker Hub 官方镜像名。国内网络拉取失败时，
# 在 Docker Desktop 里配 registry mirror，或把下面的 FROM 换成镜像站地址。

# ---------- 后端依赖 ----------
FROM python:3.12-slim AS backend-deps
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# ---------- 前端构建 ----------
FROM node:22-alpine AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --registry=https://registry.npmmirror.com
COPY frontend/ ./
# 相对路径 -> 前端和后端同源，无需 CORS，也不写死主机名
ENV VITE_API_BASE=""
RUN npm run build

# ---------- 运行时 ----------
FROM python:3.12-slim
WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=backend-deps /opt/venv /opt/venv
COPY backend/ ./backend/
COPY --from=frontend-build /app/dist ./frontend/dist

# 健康检查用 Python 而不是 curl：slim 镜像里没有 curl，装一个只为了探测
# 会凭空多出几十 MB 和额外攻击面。
RUN useradd -m -u 10001 appuser
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; r=urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2); sys.exit(0 if r.status==200 else 1)"]

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
