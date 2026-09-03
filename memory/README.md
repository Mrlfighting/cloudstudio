# 项目记忆（memory）

本目录沉淀项目的**跨会话记忆**，用纯 Markdown 编写，不依赖任何特定 agent/工具，便于切换不同模型与迁移。

## 文件索引

| 文件 | 内容 |
|---|---|
| [project.md](project.md) | 项目进度 / 当前状态 |
| [conventions.md](conventions.md) | 开发约束 / 工作方式 |
| [gotchas.md](gotchas.md) | 关键坑 / 决策记录 |

## 一句话概览

基于 Fastro 脚手架（FastAPI + PostgreSQL + SQLAlchemy 2.0 + FastCRUD + crudauth）的**公共图库平台**，已完成 **12 个功能模块**（前后端全栈），含团队空间（RBAC）与图片协同编辑（WebSocket + RabbitMQ + Redis）。当前 main 分支 HEAD=`7979fe0`，已推送 GitHub。

详细接口清单、迁移链、技术要点见 `docs/开发交接-*.md`（本地保留，不推送，含敏感信息）。
