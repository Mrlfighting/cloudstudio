# 开发约束 / 工作方式

> 用户反复强调、必须遵守的约定。

1. **一切中文**：注释、docstring、提交信息、与用户交流（提交格式如 `feat(模块): ...`）。
2. **不确定先问**：任何业务决策、配置项、接口形态、库选型等有歧义处，先 `AskUserQuestion` 或列出需补充的信息，**绝不擅自猜测**（用户原话「否则我就把你卸载了」）。
3. **新功能新建分支**：不在 main / 已有分支上直接开发（如 `feature/team-space`）。
4. **依托骨架开发**：垂直切片结构 `modules/<feature>/`（models/schemas/crud/service/routes/dependencies），复用 FastCRUD、crudauth、错误映射、分页等既有约定，不自造文件结构。
5. **密钥绝不提交**：`.env`、`backend/存储桶配置.txt`（COS 密钥）必须 gitignore；提交前查 `git status`。
6. **文件操作限定项目内**：代码/下载/缓存不得写入项目外目录。
7. **分阶段提交**：用户测试确认「可以提交」后才提交，提交前核对范围。
8. **提交信息不加 Co-Authored-By**（保持干净）。
9. **合并用 `--no-ff`**；推送前确认无敏感数据。

## 常用运行命令

```bash
# 基础设施（Docker）：postgres + redis + rabbitmq
docker compose up -d rabbitmq

# 后端（本机直跑，覆盖 .env 里 Docker 容器名为 localhost）
cd backend && CACHE_REDIS_HOST=localhost RATE_LIMITER_REDIS_HOST=localhost \
  TASKIQ_REDIS_HOST=localhost COLLAB_RABBITMQ_HOST=localhost \
  PYTHONIOENCODING=utf-8 uv run uvicorn src.interfaces.main:app --host 0.0.0.0 --port 8000 --reload

# 前端
cd frontend && npm run dev   # :5173，代理 /api → :8000（已配 ws:true）

# 测试/检查
cd backend && uv run pytest -q
cd backend && uv run ruff check src tests && uv run mypy src
cd frontend && npm run build
```
