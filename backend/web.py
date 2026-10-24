"""前端构建产物路径。

为什么要单独一个模块？
  main.py 在导入时就要决定是否挂载静态资源（挂载必须发生在应用启动时），
  而测试和脚本也要拿到同一个路径。集中在这里避免三处各写一遍路径拼接。
"""
from pathlib import Path

DIST_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
