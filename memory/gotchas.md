# 关键坑 / 决策记录

> 踩过的坑与关键决策，避免重犯。

## 选型决策

- **RBAC 选型**：`fastapi-rbac` v0.1.1 实际源码与 README 严重不符（README 的 `RBAC`/`require_role` 根本不存在，真实代码强依赖 SQLModel + loguru + JWT + 自带权限表 + 中间件），与项目 SQLAlchemy + crudauth Session/CSRF 冲突。**最终自建轻量 RBAC**（`SpaceRole` 枚举 + `ROLE_PERMISSIONS` + `has_permission` + `require_team_permission` 依赖）。

## 协同编辑

- **编辑锁 Redis 不可用必须回退内存锁，勿用 fail-open**：原 fail-open 实现（`try_acquire` 异常→True、`get_holder` 异常→None、`release` 异常→False）会导致「都能进入却无法编辑/退出」。修复为 Redis 异常时回退内存锁，语义与 Redis 一致。
- **后端 `RoomManager.join` 房间首次创建时未从落库 `edit_state` 初始化**（返回默认态 rotation=0/crop=null），导致「已保存的旋转/裁剪，刷新后新连接收到默认态」。前端已兜底（用 `detail.edit_state` 作初始视图）；**后端彻底修复待做**（房间创建时从 DB 读 `edit_state` 初始化 `Room.state`，约 3-5 行）。
- 协同编辑消息协议：`ENTER_EDIT`/`EXIT_EDIT`/`EDIT_ACTION`/`SAVE` + `INFO`/`ERROR`；`edit_state = {rotation, zoom(仅视图), crop}`，落库仅 `{rotation, crop}`。
- WebSocket 鉴权：session cookie（`auth.sessions.validate_session`），无 CSRF（握手等价 GET）。

## 图库分析缓存

- **按用户维度、随写操作（上传/删除）变化的指标不要用 `@cached`**，否则上传后刷新仍返回旧空数据。「我的空间」5 个接口不加缓存；全局指标才用 `@cached` TTL=300s。

## 前端 dev server

- **TaskStop 杀后台 `npm run dev` 会残留孤儿 Vite 进程**占用 5173/5174：`netstat -ano | grep :5173` 找 PID → `taskkill //F //PID <pid>`。
- 切换分支后旧 dev server 代理可能失效（/api 被 SPA fallback 接管返回 HTML/404）→ 杀 5173 进程后重启。
- vite 报 `Install @vitejs/plugin-vue` 多为旧进程 + 残留缓存：杀进程 + 删 `node_modules\.vite` + 重装。

## uvicorn

- **`--reload` 不拾取新文件**（Windows WatchFiles 坑）：新增模块文件后 reload 只打印 "Reloading..." 但不起新 worker。最稳：TaskStop 后重新 `uv run uvicorn`。
- `.env` 路径怪癖：settings.py 读**仓库根目录 `.env`**（不是 backend/.env）；本机直跑时根 `.env` 里的 `CACHE_REDIS_HOST=redis`（Docker 容器名）需用环境变量覆盖成 `localhost`。

## 其它

- 百度识图接口已失效（反爬 Reject），以图搜图当前无可用源。
- worker 容器退出（taskiq `--reload` extra 未声明），后台任务暂不可用。
- FastCRUD `get()` 返回 dict（非 ORM 对象），service 里要属性访问需用原生 `select()`。
- `.env`、`backend/存储桶配置.txt`、`CLAUDE.md`、`docs/开发交接*.md`、`docker-compose.yml` 均 gitignore（本地保留不推送）。
