# CLAUDE.md

> 本文件为项目记忆库合并版（原自动记忆已迁移至此），供 Claude Code 每次会话自动加载。
> 来源：开发交接文档 `docs/开发交接-20260814.md` 及原自动记忆库。

## 一、项目概述

基于 Fastro 脚手架（FastAPI + PostgreSQL + SQLAlchemy 2.0 + FastCRUD + crudauth 垂直切片架构）的二次开发，已完成两个业务模块的**前后端全栈 MVP**，并扩展了一套二级缓存基础设施：

| 模块 | 后端 | 前端 | 状态 |
|---|---|---|---|
| 用户模块 | 注册/登录/会话/权限/用户管理 | 登录/注册/个人中心/编辑资料/用户管理 | 已联调通过 |
| 图片图库 | COS 存储/审核/普通用户上传/拒绝理由 | 图片库/详情/下载/我的上传/图片管理 | 已联调通过 |
| 二级缓存 | 本地 L1 + Redis L2（列表/详情缓存、热key探测、命中率统计） | —（后端基础设施） | 已实现，待用户联调确认 |

## 二、开发约定（必须遵守）

1. **一切使用中文**：注释、docstring、提交信息、与用户交流（提交格式如 `feat(图片模块): ...`）。
2. **不确定必须先问**：任何不确定的配置/业务决策，先 AskUserQuestion 询问，经审核后再做，不擅自猜测。
3. **新功能新建分支**：不在 main/已有分支上直接开发（如 feature/picture-module、frontend-picture）。
4. **依托骨架开发**：垂直切片结构 `modules/<feature>/`（models/schemas/crud/service/routes/dependencies），复用 FastCRUD、crudauth、错误映射、分页等既有约定，不自己发明文件结构。
5. **密钥绝不提交**：.env、backend/存储桶配置.txt（COS 密钥）必须被 gitignore 屏蔽，提交前检查 `git status`。
6. **文件操作限定项目内**：代码/下载/缓存不得写入项目外目录。
7. **提交时机**：用户测试确认「可以提交」后才提交；提交前向用户核对范围。
8. **提交信息不加 Co-Authored-By**：不用 Claude Code 默认追加的 `Co-Authored-By: Claude` 行（GitHub 共同作者约定），保持提交信息干净。

## 三、分支拓扑

```
e482905 (根基线) feat(用户模块): 实现注册/登录/权限控制/用户管理与项目初始基线
├── feature/user-module  @ e482905        用户模块后端 + 初始基线
├── frontend-dev         @ 1444fca        ★前端主分支（用户+图片前端，已合并）
│   └── frontend-picture @ 1444fca        与 frontend-dev 相同，可删除
├── feature/picture-module @ 83d0f8b      图片模块后端
└── feature/cache-module  @ 83d0f8b       二级缓存模块（基于 picture-module，工作区未提交）
```

注意：仓库尚未有 main 提交，各分支以 e482905 为根。

- frontend-dev 提交链：007bc45 → 9674c17 → b9c2c55 → 1444fca
- feature/picture-module 提交链：2889289 → 83d0f8b
- feature/cache-module：基于 feature/picture-module（83d0f8b），二级缓存改动在工作区未提交

**关键分离**：前端分支（frontend-dev）与后端分支（feature/picture-module）的 backend 代码不同——本地同时跑前后端需要「检出后端源码到前端分支工作区 + docker volume 挂载」技巧（见「本地运行环境」）。

## 四、已实现接口清单

### 用户模块（/api/v1）
| 接口 | 说明 |
|---|---|
| POST /users/register | 注册（account/password/confirm_password，可选 nickname/user_profile） |
| POST /auth/login | 登录（表单 username/password → csrf_token + 会话 cookie） |
| GET /users/me | 当前用户 |
| PATCH /users/{username} | 修改个人信息 |
| POST /auth/logout | 注销（需 X-CSRF-Token） |
| GET /auth/check-auth、POST /auth/refresh-csrf | 登录态检查 / CSRF 刷新 |
| GET /users/（管理员）、PATCH /users/{username}/role（管理员） | 用户管理 / 改角色 |
| 其他 | GET /users/{username}、DELETE 软删、/db/{username} GDPR、tier、rate-limits |

### 图片模块（/api/v1/pictures）
| 接口 | 权限 | 说明 |
|---|---|---|
| POST /pictures/ | 登录用户 | 上传（multipart，自动解析宽高/格式/色彩模式，状态 pending） |
| GET /pictures/ | 登录用户 | 已发布列表（category/keyword/sort=time\|popularity 分页） |
| GET /pictures/my | 登录用户 | 我的上传（全状态 + 拒绝理由） |
| GET /pictures/manage | 管理员 | 全状态管理列表 |
| GET /pictures/{id} | 登录用户 | 详情（仅已发布） |
| GET /pictures/{id}/download | 登录用户 | 下载（计数+1 → 302 到 COS） |
| PATCH /pictures/{id} | 管理员 | 编辑元信息 |
| PATCH /pictures/{id}/status | 管理员 | 审核（approved/rejected；**拒绝必填 review_reason**） |
| DELETE /pictures/{id} | 管理员 | 软删除 |

### 二级缓存（/api/v1/cache）
| 接口 | 权限 | 说明 |
|---|---|---|
| GET /cache/stats | 管理员 | 命中率统计（local/redis 各自 hit/miss/hit_rate） |

## 五、认证机制（crudauth Session+CSRF）

**后端（infrastructure/auth/setup.py）**：
- 服务端 Session：登录 `POST /api/v1/auth/login` 表单字段固定 `username`/`password`（表单编码）→ 返回 `{csrf_token}` + 设两个 cookie：`session_id`（HttpOnly）、`csrf_token`（JS 可读）
- **写操作（POST/PATCH/DELETE）需 `X-CSRF-Token` 头**（值=csrf_token cookie）；GET 与未登录的登录请求不需要
- 角色：`user_role`（user/admin）为准，`is_superuser` 服务层同步；管理员接口依赖 `CurrentSuperUserDep`（判 is_superuser）
- 依赖注入别名在 infrastructure/dependencies.py：AsyncSessionDep/CurrentUserDep/CurrentSuperUserDep/OptionalUserDep

**前端（frontend/src/）**：
- `api/http.ts`：axios baseURL=`/api/v1`、withCredentials；请求拦截器对不安全方法自动注入 X-CSRF-Token；响应拦截器 401→清状态跳登录（登录接口自身除外）、403+X-CSRF-Error→refresh-csrf 后重放一次
- `stores/auth.ts`：**login() 不能调 initialize()**（幂等守卫 initialized 会让 user 保持 null 误判登录失败）——登录后必须直接 `userApi.getMe()`（此坑已修复）
- 路由守卫 meta：requiresAuth/requiresAdmin/guestOnly
- el-menu 必须加 `router` 属性菜单项才能跳转（此坑已修复）

**用户表**：username=登录账号、email 可空、user_role 角色来源；注册接口 `POST /api/v1/users/register`。

## 六、技术要点备忘

- **前端栈**：Vue3+Vite+TS+Element Plus+Pinia+Vue Router+Axios；`frontend/src/` 结构（api/types/stores/router/views/components）
- **图片存储**：腾讯云 COS（ap-guangzhou，公有读桶 mrlphotho-1467406694），SDK cos-python-sdk-v5 + Pillow 解析；上传 key 前缀 `pictures/<uuid>.<ext>`
- **数据库迁移**：44c893efd0a2（初始）→ c63446b89172（pictures）→ 29843fe6a79d（review_reason）
- **标签搜索**：JSON 列用 JSONB `@>` 结构匹配（避免 ensure_ascii 转义导致中文失配）
- **角色同步**：user_role 为准，is_superuser 服务层显式同步（FastCRUD 走 Core UPDATE 不触发 @validates）
- **二级缓存**（feature/cache-module，基础设施 `infrastructure/cache/`）：L1 本地 `MemoryBackend`（cachetools.TTLCache）+ L2 复用 `RedisBackend`；核心 `TwoLevelCacheManager`（get/put/evict/invalidate_by_prefix/get_or_load/is_hot_key/promote_to_local/stats）+ `@cached` 方法级装饰器；service 层 `get`/`list_user` 接缓存，写操作（upload/update/audit/delete/download）后失效。详细设计见 `docs/缓存设计-20260814.md`
- **缓存 key**：`pic:list:{scope}:{category}:{sort}:{page}:{size}:{kw8}`（关键词 md5 取 8 位）、`pic:detail:{id}`、`pic:hot:{id}`；TTL 差异化（popularity 30s / time·详情 300s，L1 统一 60s）；热key惰性 INCR 计数达阈值提升到本地
- **缓存降级**：Redis 异常 fail-open（L1+DB 直读 + `logger.warning(extra={"reason":"redis_unavailable"})`）

## 七、本地运行环境（Windows 11 + Git Bash + Docker Desktop）

**docker compose 栈**（根目录 docker-compose.yml，**被 gitignore 忽略**，是 bp 生成文件）：
- `api`（8000）：**volume 挂载 `./backend/src:/app/src` 和 `./backend/tests:/app/tests`**——容器实时反映当前分支后端代码，改代码自动热重载（uvicorn --reload）
- `postgres`（5432）、`redis`（6379）、`worker`（已知退出，见「遗留问题」）
- 重启：`docker compose up -d`；重新构建（依赖变更时）：`docker compose up -d --build api`
- 注意：Docker Desktop 引擎重启会导致容器 Exit，`docker info` 超时需等就绪

**配置**：
- `backend/.env`（gitignored）：含 COS_SECRET_ID/KEY/REGION(ap-guangzhou)/BUCKET(mrlphotho-1467406694)、SESSION_SECURE_COOKIES=false（本地 http 必需）、SESSION_BACKEND=redis

**前端**（frontend/，Vue3+Vite+Element Plus）：
- dev server 5173，`vite.config.ts` 代理 `/api` → `http://localhost:8000`（不 rewrite）
- **坑**：切换 git 分支后旧 dev server 代理可能失效（/api 被 SPA fallback 接管返回 HTML/404）→ 必须 taskkill 5173 进程后重启 `npm run dev`
- 构建：`npm run build`（vue-tsc 类型检查）

**分支分离的本地验证技巧**（重要）：前端分支（frontend-dev）与图片后端分支（feature/picture-module）backend 代码不同。要在前端分支跑含图片后端的容器：
```bash
git checkout feature/picture-module -- backend/src/modules/pictures backend/src/infrastructure/config/settings.py backend/src/interfaces/api/v1/__init__.py backend/src/modules/__init__.py backend/src/modules/common/constants.py backend/src/modules/common/exceptions.py
```
（检出仅本地验证用，提交时只 add frontend/，`git reset HEAD backend/` 取消误暂存）

**Windows 控制台坑**：cp1252 编码打印中文会 UnicodeEncodeError → 加 `PYTHONIOENCODING=utf-8` 或避免 print 中文；Git Bash 里 `docker compose ps` 等命令偶尔超时需后台跑。

## 八、运行与测试

```bash
# 后端
docker compose up -d                          # api:8000 postgres:5432 redis:6379
docker compose up -d --build api              # 依赖变更时重建

# 前端
cd frontend && npm run dev                    # :5173，代理 /api → :8000

# 测试（需 Docker，testcontainers 固定 postgres:16-alpine）
cd backend && uv run pytest -q                # 约 287 项（含二级缓存 23 项）
cd backend && uv run ruff check src tests && uv run mypy src
```

## 九、遗留问题与待办

1. **worker 容器退出**（Exit 1）：模板 bug，`taskiq[reload]` extra 未声明（backend/pyproject.toml）。不影响 API/前端，后台任务暂不可用。
2. **docker 构建文件未提交**：`backend/Dockerfile` 和 `.dockerignore` 是本地修复（COPY 路径改 backend/ 前缀、context 修复），因与 bp 模板耦合而未提交，各分支工作区以未跟踪文件存在。
3. **admin 弱密码**：admin/adminpassword（.env 路径怪癖导致 ADMIN_* 未被容器读取，用脚本默认值）。用户可随时要求重置。
4. **frontend-picture 分支可删除**：与 frontend-dev 完全相同（1444fca），用户已同意合并但未删。
5. **mrl2 用户密码含全角感叹号**：`luobo123！`（全角 U+FF01）可登录，半角 `!` 会 401。
6. **docker-compose.yml 被 gitignore**（bp 生成物）。
7. **二级缓存未提交**：feature/cache-module 的改动（含 `cachetools` 依赖）在工作区，待用户联调确认后再提交。
8. **uv.lock 未同步**：`cachetools>=5.5.0` 已加入 backend/pyproject.toml，但 uv.lock 尚未重新生成（本次环境 uv 不可用，用 Anaconda pip `--target` 装进 venv）——用户本地跑 `cd backend && uv sync` 同步锁文件。
